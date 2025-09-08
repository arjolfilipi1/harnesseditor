from typing import List, Dict
from peewee import prefetch
from database.models import (
    Harness, Connector, Pin, Node, Wire, HarnessBranch, 
    BranchProtection, BranchPath, ConnectorType, ProtectionType, WireType
)
from models.harness_models import (
    WiringHarness, Connector as ConnectorModel, Pin as PinModel,
    Node as NodeModel, Wire as WireModel, HarnessBranch as HarnessBranchModel,
    BranchProtection as BranchProtectionModel, WireType as WireTypeModel,
    ProtectionType as ProtectionTypeModel, ConnectorType as ConnectorTypeModel
)

class DataLoader:
    @staticmethod
    def load_harness(harness_id: str) -> WiringHarness:
        """Load a complete harness with all related data"""
        # Prefetch all related data in optimized queries
        harness_query = Harness.select().where(Harness.id == harness_id)
        
        connectors = Connector.select().where(Connector.harness == harness_id)
        pins = Pin.select().where(Pin.connector.in_(connectors))
        nodes = Node.select().where(Node.harness == harness_id)
        wires = Wire.select().where(Wire.harness == harness_id)
        branches = HarnessBranch.select().where(HarnessBranch.harness == harness_id)
        protections = BranchProtection.select().where(BranchProtection.harness == harness_id)
        branch_paths = BranchPath.select().where(BranchPath.branch.in_(branches))
        
        # Execute prefetch for optimal performance
        harness_data = prefetch(
            harness_query,
            connectors, pins, nodes, wires, branches, protections, branch_paths
        )
        
        if not harness_data:
            raise ValueError(f"Harness with ID {harness_id} not found")
        else:
            harness_data = harness_data[0]
        # Build the domain models
        protection_models = {
            prot.id: BranchProtectionModel(
                id=prot.id,
                type=ProtectionTypeModel[prot.type.id],
                part_number=prot.part_number,
                diameter_mm=prot.diameter_mm
            )
            for prot in protections
        }
        
        connector_models = {}
        for connector in connectors:
            connector_pins = {pin.number: PinModel(
                number=pin.number,
                gender=pin.gender,
                seal=pin.seal_type
            ) for pin in pins if pin.connector.id == connector.id}
            
            connector_models[connector.id] = ConnectorModel(
                id=connector.id,
                name=connector.name,
                type=ConnectorTypeModel[connector.type.id],
                part_number=connector.part_number,
                gender=connector.gender,
                seal=connector.seal_type,
                pins=connector_pins,
                position=(float(connector.position_x), float(connector.position_y))
            )
        
        node_models = {
            node.id: NodeModel(
                id=node.id,
                harness_id=harness_id,
                name=node.name,
                type=node.type,
                connector_id=node.connector.id if node.connector else None,
                position=(float(node.position_x), float(node.position_y))
            )
            for node in nodes
        }
        
        wire_models = {
            wire.id: WireModel(
                id=wire.id,
                harness_id=harness_id,
                type=WireTypeModel[wire.type.id],
                color=wire.color_code,
                from_node_id=wire.from_node.id,
                from_pin=wire.from_connector_pin,
                to_node_id=wire.to_node.id,
                to_pin=wire.to_connector_pin,
                calculated_length_mm=float(wire.calculated_length_mm) if wire.calculated_length_mm else None
            )
            for wire in wires
        }
        
        branch_models = {}
        for branch in branches:
            # Get path points for this branch
            path_points = [
                (float(path.position_x), float(path.position_y))
                for path in branch_paths 
                if path.branch.id == branch.id
            ]
            path_points.sort(key=lambda x: x[0])  # Sort by sequence number via position_x as proxy
            
            branch_models[branch.id] = HarnessBranchModel(
                id=branch.id,
                harness_id=harness_id,
                name=branch.name,
                protection_id=branch.protection.id if branch.protection else None,
                path_points=path_points,
                nodes=[node.id for node in nodes if node.harness.id == harness_id]  # Simplified
            )
        
        return WiringHarness(
            name=harness_data.name,
            part_number=harness_data.part_number,
            connectors=connector_models,
            wires=wire_models,
            branches=branch_models,
            protections=protection_models
        )
    
    @staticmethod
    def load_all_harnesses() -> List[WiringHarness]:
        """Load all harnesses from the database"""
        harnesses = []
        for harness in Harness.select():
            try:
                harnesses.append(DataLoader.load_harness(harness.id))
            except ValueError:
                continue  # Skip harnesses that can't be loaded
        return harnesses