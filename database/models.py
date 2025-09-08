from peewee import *
from .core import BaseModel
from playhouse.hybrid import hybrid_property
import math

class Harness(BaseModel):
    id = CharField(primary_key=True, max_length=20)
    name = CharField(max_length=100)
    part_number = CharField(max_length=50)
    revision = IntegerField(default=1)

class ConnectorType(BaseModel):
    id = CharField(primary_key=True, max_length=10)
    name = CharField(max_length=50)
    description = TextField(null=True)

class ProtectionType(BaseModel):
    id = CharField(primary_key=True, max_length=20)
    name = CharField(max_length=50)
    description = TextField(null=True)

class WireType(BaseModel):
    id = CharField(primary_key=True, max_length=20)
    name = CharField(max_length=50)
    cross_section_mm2 = DecimalField(max_digits=3, decimal_places=2)
    description = TextField(null=True)

class Connector(BaseModel):
    id = CharField(primary_key=True, max_length=20)
    harness = ForeignKeyField(Harness, backref='connectors', on_delete='CASCADE')
    name = CharField(max_length=100)
    type = ForeignKeyField(ConnectorType, backref='connectors')
    part_number = CharField(max_length=50, null=True)
    gender = CharField(choices=['MALE', 'FEMALE'])
    seal_type = CharField(choices=['UNSEALED', 'CONNECTOR_SEALED', 'FULLY_SEALED'])
    position_x = DecimalField(max_digits=10, decimal_places=2, default=0.0)
    position_y = DecimalField(max_digits=10, decimal_places=2, default=0.0)

class Pin(BaseModel):
    connector = ForeignKeyField(Connector, backref='pins', on_delete='CASCADE')
    number = CharField(max_length=10)
    gender = CharField(choices=['MALE', 'FEMALE'])
    seal_type = CharField(choices=['UNSEALED', 'CONNECTOR_SEALED', 'FULLY_SEALED'])
    
    class Meta:
        indexes = (
            (('connector', 'number'), True),  # Unique constraint
        )

class BranchProtection(BaseModel):
    id = CharField(primary_key=True, max_length=20)
    harness = ForeignKeyField(Harness, backref='protections', on_delete='CASCADE')
    type = ForeignKeyField(ProtectionType, backref='protections')
    part_number = CharField(max_length=50, null=True)
    diameter_mm = DecimalField(max_digits=5, decimal_places=2, null=True)

class Node(BaseModel):
    id = CharField(primary_key=True, max_length=20)
    harness = ForeignKeyField(Harness, backref='nodes', on_delete='CASCADE')
    name = CharField(max_length=100, null=True)
    type = CharField(choices=['CONNECTOR', 'SPLICE', 'GROUND', 'TERMINAL'])
    connector = ForeignKeyField(Connector, null=True, backref='nodes')
    position_x = DecimalField(max_digits=10, decimal_places=2)
    position_y = DecimalField(max_digits=10, decimal_places=2)

class Wire(BaseModel):
    id = CharField(primary_key=True, max_length=20)
    harness = ForeignKeyField(Harness, backref='wires', on_delete='CASCADE')
    type = ForeignKeyField(WireType, backref='wires')
    color_code = CharField(max_length=20)
    from_node = ForeignKeyField(Node, backref='outgoing_wires')
    from_connector_pin = CharField(max_length=10, null=True)
    to_node = ForeignKeyField(Node, backref='incoming_wires')
    to_connector_pin = CharField(max_length=10, null=True)
    calculated_length_mm = DecimalField(max_digits=8, decimal_places=2, null=True)
    
    class Meta:
        indexes = (
            (('harness', 'from_node', 'from_connector_pin', 'to_node', 'to_connector_pin'), True),
        )

class HarnessBranch(BaseModel):
    id = CharField(primary_key=True, max_length=20)
    harness = ForeignKeyField(Harness, backref='branches', on_delete='CASCADE')
    name = CharField(max_length=100)
    protection = ForeignKeyField(BranchProtection, null=True, backref='branches')

class BranchSegment(BaseModel):
    branch = ForeignKeyField(HarnessBranch, backref='segments', on_delete='CASCADE')
    wire = ForeignKeyField(Wire, backref='segments', on_delete='CASCADE')
    start_node = ForeignKeyField(Node, backref='segment_starts')
    end_node = ForeignKeyField(Node, backref='segment_ends')
    segment_length_mm = DecimalField(max_digits=8, decimal_places=2, null=True)
    sequence_number = IntegerField()
    
    class Meta:
        indexes = (
            (('branch', 'wire', 'start_node', 'end_node'), True),
        )

class BranchPath(BaseModel):
    branch = ForeignKeyField(HarnessBranch, backref='path_points', on_delete='CASCADE')
    sequence_number = IntegerField()
    position_x = DecimalField(max_digits=10, decimal_places=2)
    position_y = DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        primary_key = CompositeKey('branch', 'sequence_number')
    
    @hybrid_property
    def position(self):
        return (self.position_x, self.position_y)