import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QDockWidget,
    QWidget, QVBoxLayout, QLabel, QLineEdit, QAction, QToolBar,
    QGraphicsRectItem, QGraphicsPathItem, QColorDialog
)
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt, QPointF


class SymbolItem(QGraphicsRectItem):
    """Basic symbol with a name and position properties."""
    def __init__(self, x, y, name="Symbol"):
        super().__init__(0, 0, 60, 40)
        self.setPos(x, y)
        self.name = name
        self.connected_wires = []  # track attached wires
        self.setFlags(
            QGraphicsRectItem.ItemIsMovable |
            QGraphicsRectItem.ItemIsSelectable
        )
        self.setBrush(Qt.lightGray)

    def get_center(self):
        rect = self.rect()
        return self.scenePos() + rect.center()

    def get_edge_point(self, target_point: QPointF):
        """Find the closest edge point of the rectangle to target_point."""
        rect = self.rect().translated(self.scenePos())
        x = min(max(target_point.x(), rect.left()), rect.right())
        y = min(max(target_point.y(), rect.top()), rect.bottom())

        dx_left = abs(target_point.x() - rect.left())
        dx_right = abs(target_point.x() - rect.right())
        dy_top = abs(target_point.y() - rect.top())
        dy_bottom = abs(target_point.y() - rect.bottom())

        min_dist = min(dx_left, dx_right, dy_top, dy_bottom)
        if min_dist == dx_left:
            return QPointF(rect.left(), y)
        elif min_dist == dx_right:
            return QPointF(rect.right(), y)
        elif min_dist == dy_top:
            return QPointF(x, rect.top())
        else:
            return QPointF(x, rect.bottom())

    def itemChange(self, change, value):
        """Notify connected wires when this symbol moves."""
        if change == QGraphicsRectItem.ItemPositionChange:
            for wire in self.connected_wires:
                wire.update_path()
        return super().itemChange(change, value)


class WireItem(QGraphicsPathItem):
    """Wire with 90-degree bends between two symbols."""
    def __init__(self, start_item, end_item, color=Qt.black):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.color = QColor(color)

        self.setPen(QPen(self.color, 2))
        self.setFlags(QGraphicsPathItem.ItemIsSelectable)

        # register with symbols
        start_item.connected_wires.append(self)
        end_item.connected_wires.append(self)

        self.update_path()

    def update_path(self):
        start = self.start_item.get_edge_point(self.end_item.get_center())
        end = self.end_item.get_edge_point(self.start_item.get_center())

        path = QPainterPath(start)
        mid_x = (start.x() + end.x()) / 2
        path.lineTo(mid_x, start.y())
        path.lineTo(mid_x, end.y())
        path.lineTo(end)

        self.setPath(path)

    def set_color(self, color: QColor):
        self.color = color
        self.setPen(QPen(self.color, 2))


class PropertiesPanel(QWidget):
    """Dockable widget showing properties of selected item."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Symbol properties
        self.name_label = QLabel("Name:")
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        self.pos_label = QLabel("Position: (x=0, y=0)")
        layout.addWidget(self.pos_label)

        # Wire properties
        self.start_label = QLabel("Start: -")
        self.end_label = QLabel("End: -")
        self.color_label = QLabel("Color:")
        self.color_button = QAction("Pick Color", self)
        layout.addWidget(self.start_label)
        layout.addWidget(self.end_label)
        layout.addWidget(self.color_label)

        self.setLayout(layout)
        self.current_item = None

        # connect edits
        self.name_edit.editingFinished.connect(self.rename_symbol)

    def update_properties(self, item):
        self.current_item = item
        if isinstance(item, SymbolItem):
            self.name_edit.setEnabled(True)
            self.name_edit.setText(item.name)
            pos = item.scenePos()
            self.pos_label.setText(f"Position: (x={int(pos.x())}, y={int(pos.y())})")
            self.start_label.setText("Start: -")
            self.end_label.setText("End: -")
            self.color_label.setText("Color: -")

        elif isinstance(item, WireItem):
            self.name_edit.setEnabled(False)
            self.pos_label.setText("Position: -")
            self.start_label.setText(f"Start: {item.start_item.name}")
            self.end_label.setText(f"End: {item.end_item.name}")
            self.color_label.setText(f"Color: {item.color.name()}")

    def rename_symbol(self):
        if isinstance(self.current_item, SymbolItem):
            self.current_item.name = self.name_edit.text()

    def pick_color_for_wire(self, wire: WireItem):
        color = QColorDialog.getColor(wire.color, self, "Pick Wire Color")
        if color.isValid():
            wire.set_color(color)
            self.color_label.setText(f"Color: {wire.color.name()}")


class DiagramScene(QGraphicsScene):
    def __init__(self, properties_panel):
        super().__init__()
        self.mode = "select"
        self.start_item = None
        self.properties_panel = properties_panel

    def set_mode(self, mode):
        self.mode = mode

    def mousePressEvent(self, event):
        if self.mode == "add_symbol":
            pos = event.scenePos()
            symbol = SymbolItem(pos.x(), pos.y(), name=f"Symbol{len(self.items())}")
            self.addItem(symbol)

        elif self.mode == "add_wire":
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(item, SymbolItem):
                self.start_item = item
        else:
            super().mousePressEvent(event)

        # Update properties panel on selection
        selected = self.selectedItems()
        if selected:
            self.properties_panel.update_properties(selected[0])

    def mouseReleaseEvent(self, event):
        if self.mode == "add_wire" and self.start_item:
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(item, SymbolItem) and item is not self.start_item:
                wire = WireItem(self.start_item, item)
                self.addItem(wire)
            self.start_item = None
        else:
            super().mouseReleaseEvent(event)


class DiagramEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wiring Diagram Editor (Selectable Wires + Properties)")
        self.resize(1000, 600)

        # Properties panel
        self.properties_panel = PropertiesPanel()
        dock = QDockWidget("Properties", self)
        dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Scene + View
        self.scene = DiagramScene(self.properties_panel)
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        # Toolbar
        toolbar = QToolBar("Tools")
        self.addToolBar(toolbar)

        select_action = QAction("Select", self)
        select_action.triggered.connect(lambda: self.scene.set_mode("select"))
        toolbar.addAction(select_action)

        symbol_action = QAction("Add Symbol", self)
        symbol_action.triggered.connect(lambda: self.scene.set_mode("add_symbol"))
        toolbar.addAction(symbol_action)

        wire_action = QAction("Add Wire", self)
        wire_action.triggered.connect(lambda: self.scene.set_mode("add_wire"))
        toolbar.addAction(wire_action)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DiagramEditor()
    window.show()
    sys.exit(app.exec_())
