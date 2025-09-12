import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QDockWidget,
    QWidget, QVBoxLayout, QLabel, QLineEdit, QAction, QToolBar,
    QGraphicsRectItem, QGraphicsPathItem, QColorDialog, QPushButton, QGraphicsSimpleTextItem,
    QListWidget,QFormLayout,QComboBox,QGraphicsEllipseItem, QGraphicsLineItem
)
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtWidgets import QGraphicsItem
from models.harness_models import *
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Dict, Optional, Tuple
# ------------------------------
# Undo/Redo command base
# ------------------------------
class Command:
    def undo(self): pass
    def redo(self): pass


# ------------------------------
# Items
# ------------------------------
class BranchSegmentItem(QGraphicsLineItem):
    counter = 1
    def __init__(self, segment: BranchSegment, start_item, end_item):
        """
        start_item and end_item can be NodeItem or SymbolItem
        """
        super().__init__()
        self.segment = segment
        self.start_item = start_item
        self.end_item = end_item
        self.data_class = Connector(id="C1",    name="Main Connector",    type=ConnectorType.OTHER,    gender=Gender.MALE,    seal=SealType.UNSEALED,    part_number="123-456",position =   (self.scenePos().x(), self.scenePos().y()))
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setPen(QPen(Qt.blue, 2))

        self.name = segment.name or f"Segment{BranchSegmentItem.counter}"
        BranchSegmentItem.counter += 1

        # register with endpoints
        if hasattr(self.start_item, "connected_wires"):
            self.start_item.connected_wires.append(self)
        if hasattr(self.end_item, "connected_wires"):
            self.end_item.connected_wires.append(self)

        self.update_path()

    def update_path(self):
        start = self.start_item.scenePos()
        if isinstance(self.start_item, SymbolItem):
            start = self.start_item.get_center()

        end = self.end_item.scenePos()
        if isinstance(self.end_item, SymbolItem):
            end = self.end_item.get_center()

        self.setLine(start.x(), start.y(), end.x(), end.y())

    def item_type(self):
        return "BranchSegment"

    def __str__(self):
        return self.name

class SymbolItem(QGraphicsRectItem):
    def __init__(self, x, y, name="Symbol"):
        super().__init__(0, 0, 60, 40)
        self.setPos(x, y)
        self.name = name
        self.connected_wires = []

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.data_class = Connector(id="C1",    name="Main Connector",    type=ConnectorType.OTHER,    gender=Gender.MALE,    seal=SealType.UNSEALED,    part_number="123-456",position =   (self.scenePos().x(), self.scenePos().y()))
        self.setZValue(1)
        self.setBrush(Qt.lightGray)

        # Label above symbol
        self.label = QGraphicsSimpleTextItem(self.name, self)
        self.label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.update_label_pos()

    def update_label_pos(self):
        self.label.setPos(
            self.rect().center().x() - self.label.boundingRect().width() / 2,
            -self.label.boundingRect().height() - 2
        )

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.data_class.position =   (self.scenePos().x(), self.scenePos().y())
            for wire in list(self.connected_wires):
                wire.update_path()
        return super().itemChange(change, value)

    def get_center(self) -> QPointF:
        return self.scenePos() + self.rect().center()

class NodeItem(QGraphicsEllipseItem):
    counter = 1
    def __init__(self,  x, y, node = None):
        super().__init__(-10, -10, 20, 20)  # circle 20px
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        self.setBrush(Qt.yellow)
        self.name = (node.name if node else None)  or f"Node{NodeItem.counter}"
        self.data_class = Node(id= self.name,
        harness_id = "default",
        name= self.name,
        type= NodeType.BREAKOUT) if node == None else node
        NodeItem.counter += 1
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.data_class.position =   (self.scenePos().x(), self.scenePos().y())
            for wire in list(self.connected_wires):
                wire.update_path()
        return super().itemChange(change, value)
    def item_type(self):
        return "Node"

    def __str__(self):
        return self.name

class WireItem(QGraphicsPathItem):
    counter = 1
    def __init__(self, start_item: SymbolItem, end_item: SymbolItem, color=QColor("black")):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.color = QColor(color)
        self.name = f"Wire{WireItem.counter}"
        WireItem.counter += 1
        self.data_class = Wire(id = self.name,harness_id= "default",color='BK',type= WireType.FLRY_B_0_35,from_node_id = start_item.name,to_node_id=end_item.name )
        self.setPen(QPen(self.color, 2))
        self.setFlags(QGraphicsPathItem.ItemIsSelectable | QGraphicsPathItem.ItemIsFocusable)
        self.setZValue(0)

        start_item.connected_wires.append(self)
        end_item.connected_wires.append(self)

        self.update_path()

    def update_path(self):
        """Connect at side midpoints and offset for parallel wires."""
        if not (self.start_item and self.end_item):
            return

        def side_midpoint(symbol: SymbolItem, target: QPointF) -> QPointF:
            rect_scene = symbol.rect().translated(symbol.scenePos())
            dx_left = abs(target.x() - rect_scene.left())
            dx_right = abs(target.x() - rect_scene.right())
            dy_top = abs(target.y() - rect_scene.top())
            dy_bottom = abs(target.y() - rect_scene.bottom())
            side = min(
                [("left", dx_left), ("right", dx_right),
                 ("top", dy_top), ("bottom", dy_bottom)],
                key=lambda t: t[1]
            )[0]
            if side == "left":
                return QPointF(rect_scene.left(), rect_scene.center().y())
            elif side == "right":
                return QPointF(rect_scene.right(), rect_scene.center().y())
            elif side == "top":
                return QPointF(rect_scene.center().x(), rect_scene.top())
            else:
                return QPointF(rect_scene.center().x(), rect_scene.bottom())

        start = side_midpoint(self.start_item, self.end_item.get_center())
        end = side_midpoint(self.end_item, self.start_item.get_center())

        siblings = [
            w for w in self.start_item.connected_wires
            if (w.start_item is self.start_item and w.end_item is self.end_item) or
               (w.start_item is self.end_item and w.end_item is self.start_item)
        ]
        index = siblings.index(self)
        offset = (index - (len(siblings) - 1) / 2) * 10

        path = QPainterPath()
        path.moveTo(start)

        if abs(start.y() - end.y()) < 6:
            path.lineTo(end + QPointF(0, offset))
        elif abs(start.x() - end.x()) < 6:
            path.lineTo(end + QPointF(offset, 0))
        else:
            mid_x = (start.x() + end.x()) / 2.0 + offset
            path.lineTo(mid_x, start.y())
            path.lineTo(mid_x, end.y())
            path.lineTo(end)

        self.prepareGeometryChange()
        self.setPath(path)

    def set_color(self, color: QColor):
        self.color = QColor(color)
        self.setPen(QPen(self.color, 2))


class PropertiesWidget(QWidget):
    def __init__(self, obj):
        super().__init__()
        self.obj = obj
        self.form = QFormLayout(self)
        self.editors = {}  # map: field_name -> widget
        self.build_form()

    def build_form(self):
        for f in fields(self.obj):
            value = getattr(self.obj, f.name)

            if isinstance(value, Enum):
                editor = QComboBox()
                for enum_member in f.type:  # iterate enum
                    editor.addItem(enum_member.value, enum_member)
                editor.setCurrentText(value.value)

                editor.currentIndexChanged.connect(
                    lambda i, fn=f.name, ed=editor: setattr(
                        self.obj, fn, ed.itemData(i))
                )

            elif isinstance(value, str) or value is None:
                editor = QLineEdit("" if value is None else str(value))
                editor.editingFinished.connect(
                    lambda fn=f.name, ed=editor: setattr(self.obj, fn, ed.text())
                )

            elif isinstance(value, tuple):
                editor = QLineEdit(str(value))  # could split into 2 spinboxes
                editor.editingFinished.connect(
                    lambda fn=f.name, ed=editor: setattr(
                        self.obj, fn, tuple(map(float, ed.text().strip("()").split(","))))
                )

            else:
                editor = QLineEdit(str(value))
                editor.editingFinished.connect(
                    lambda fn=f.name, ed=editor: setattr(self.obj, fn, ed.text())
                )

            self.form.addRow(f.name, editor)
            self.editors[f.name] = editor
# ------------------------------
# Properties Panel
# ------------------------------
class PropertiesPanel(QWidget):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.current_layout = None
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)

        self.main_layout.addLayout(layout)
        self.current_layout = layout
        self.current_item = None
    def replace_layout(self,new_layout):
        # 1. Remove contents of the old layout
        if self.current_layout:
            while self.current_layout.count():
                item = self.current_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater() # Delete the widget if it exists
                elif item.layout():
                    pass 

            # 2. Delete the old layout
            self.current_layout.deleteLater() 
            self.current_layout = None

        self.current_layout = new_layout
        self.main_layout.addLayout(self.current_layout)

    def update_properties(self, item):
        self.current_item = item
        layout = QVBoxLayout()
        
        pw =  PropertiesWidget(item.data_class)
        layout.addWidget(pw)
        self.replace_layout(layout)


# ------------------------------
# Diagram Scene
# ------------------------------
class DiagramScene(QGraphicsScene):
    def __init__(self, editor, properties_panel: PropertiesPanel):
        super().__init__()
        self.editor = editor
        self.mode = "select"
        self.start_item = None
        self.properties_panel = properties_panel
        self.symbol_counter = 1
        self.selectionChanged.connect(self.on_selection_changed)

    def set_mode(self, mode: str):
        self.mode = mode
        self.start_item = None

    def on_selection_changed(self):
        selected = self.selectedItems()
        if selected:
            self.properties_panel.update_properties(selected[0])
        

    def mousePressEvent(self, event):
        if self.mode == "add_symbol":
            pos = event.scenePos()
            name = f"C{self.symbol_counter}"
            self.symbol_counter += 1
            symbol = SymbolItem(pos.x(), pos.y(), name=name)
            self.editor.push_command(AddSymbolCommand(self, symbol))
            self.clearSelection()
            symbol.setSelected(True)
            self.properties_panel.update_properties(symbol)
            return
        elif self.mode == "add_node":
            pos = event.scenePos()
            self.symbol_counter += 1
            node = NodeItem(pos.x(), pos.y())
            self.editor.push_command(AddNodeCommand(self, node_item=node))
            self.clearSelection()
            node.setSelected(True)
            self.properties_panel.update_properties(node)
            return
        elif self.mode == "add_wire":
            item = self.itemAt(event.scenePos(), self.views()[0].transform()) if self.views() else None
            if isinstance(item, SymbolItem):
                self.start_item = item
            else:
                self.start_item = None
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == "add_wire" and self.start_item:
            item = self.itemAt(event.scenePos(), self.views()[0].transform()) if self.views() else None
            if isinstance(item, SymbolItem) and item is not self.start_item:
                wire = WireItem(self.start_item, item)
                self.editor.push_command(AddWireCommand(self, wire))
                self.clearSelection()
                wire.setSelected(True)
                self.properties_panel.update_properties(wire)
            self.start_item = None
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        selected = self.selectedItems()
        if selected and isinstance(selected[0], SymbolItem):
            self.properties_panel.update_properties(selected[0])

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform()) if self.views() else None
        if isinstance(item, SymbolItem):
            # record a move command on double click release
            pass
        super().mouseDoubleClickEvent(event)


# ------------------------------
# Commands
# ------------------------------
class AddSymbolCommand(Command):
    def __init__(self, scene, symbol):
        self.scene = scene
        self.symbol = symbol

    def undo(self): 
        self.scene.removeItem(self.symbol)
        self.scene.editor.refresh_list()
    def redo(self): 
        self.scene.addItem(self.symbol)
        self.scene.editor.refresh_list()


class AddWireCommand(Command):
    def __init__(self, scene, wire):
        self.scene = scene
        self.wire = wire

    def undo(self): 
        self.scene.removeItem(self.wire)
        self.scene.editor.refresh_list()
    def redo(self): 
        self.scene.addItem(self.wire)
        self.scene.editor.refresh_list()
        
class AddNodeCommand(Command):
    def __init__(self,scene, node_item):
        self.scene = scene
        self.node_item = node_item

    def undo(self):
        self.scene.removeItem(self.node_item)
        self.scene.editor.refresh_list()

    def redo(self):
        self.scene.addItem(self.node_item)
        self.scene.editor.refresh_list()
        
class RenameSymbolCommand(Command):
    def __init__(self, symbol, old_name, new_name):
        self.symbol = symbol
        self.old = old_name
        self.new = new_name

    def undo(self):
        self.symbol.name = self.old
        self.symbol.label.setText(self.old)
        self.symbol.update_label_pos()

    def redo(self):
        self.symbol.name = self.new
        self.symbol.label.setText(self.new)
        self.symbol.update_label_pos()


class ChangeWireColorCommand(Command):
    def __init__(self, wire, old_color, new_color):
        self.wire = wire
        self.old = QColor(old_color)
        self.new = QColor(new_color)

    def undo(self): self.wire.set_color(self.old)
    def redo(self): self.wire.set_color(self.new)


# ------------------------------
# Main Editor
# ------------------------------
class DiagramEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wiring Diagram Editor (with Undo/Redo)")
        self.resize(1000, 700)

        self.undo_stack = []
        self.redo_stack = []

        self.properties_panel = PropertiesPanel(self)
        dock = QDockWidget("Properties", self)
        dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        self.scene = DiagramScene(self, self.properties_panel)
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)

        select_action = QAction("Select", self)
        select_action.triggered.connect(lambda: self.scene.set_mode("select"))
        toolbar.addAction(select_action)

        symbol_action = QAction("Add Connector", self)
        symbol_action.triggered.connect(lambda: self.scene.set_mode("add_symbol"))
        toolbar.addAction(symbol_action)
        
        node_action = QAction("Add Node", self)
        node_action.triggered.connect(lambda: self.scene.set_mode("add_node"))
        toolbar.addAction(node_action)
        
        wire_action = QAction("Add Wire", self)
        wire_action.triggered.connect(lambda: self.scene.set_mode("add_wire"))
        toolbar.addAction(wire_action)

        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        self.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        self.addAction(redo_action)
        self.create_list_dock()
    def create_list_dock(self):
        self.list_widget = QListWidget()
        dock = QDockWidget("Elements", self)
        dock.setWidget(self.list_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        
        self.list_widget.itemClicked.connect(self.select_item_from_list)
        
    def refresh_list(self):
        self.list_widget.clear()
        for item in self.scene.items():
            if isinstance(item, (SymbolItem, WireItem)):
                self.list_widget.addItem(item.name)
                
    def select_item_from_list(self, list_item):
        name = list_item.text()
        for item in self.scene.items():
            if isinstance(item, (SymbolItem, WireItem)) and item.name == name:
                self.scene.clearSelection()
                item.setSelected(True)
                self.view.centerOn(item)
                break
    # --- Undo/Redo stack management ---
    def push_command(self, command):
        command.redo()
        self.undo_stack.append(command)
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            cmd = self.undo_stack.pop()
            cmd.undo()
            self.redo_stack.append(cmd)

    def redo(self):
        if self.redo_stack:
            cmd = self.redo_stack.pop()
            cmd.redo()
            self.undo_stack.append(cmd)


# ------------------------------
# Run
# ------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DiagramEditor()
    window.show()
    sys.exit(app.exec_())
