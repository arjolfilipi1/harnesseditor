import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QDockWidget,
    QWidget, QVBoxLayout, QLabel, QLineEdit, QAction, QToolBar, QGraphicsRectItem,
    QGraphicsPathItem
)
from PyQt5.QtGui import QPainterPath, QPen
from PyQt5.QtCore import Qt, QPointF


class SymbolItem(QGraphicsRectItem):
    """Basic symbol with a name and position properties."""
    def __init__(self, x, y, name="Symbol"):
        super().__init__(0, 0, 60, 40)
        self.setPos(x, y)
        self.name = name
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

        # Snap to nearest edge
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


class WireItem(QGraphicsPathItem):
    """Wire with 90-degree bends between two symbols."""
    def __init__(self, start_item, end_item):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.setPen(QPen(Qt.black, 2))
        self.update_path()

    def update_path(self):
        start = self.start_item.get_edge_point(self.end_item.get_center())
        end = self.end_item.get_edge_point(self.start_item.get_center())

        path = QPainterPath(start)

        # Simple 90-degree routing: go halfway in x, then down to end
        mid_x = (start.x() + end.x()) / 2
        path.lineTo(mid_x, start.y())
        path.lineTo(mid_x, end.y())
        path.lineTo(end)

        self.setPath(path)


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

    def mouseReleaseEvent(self, event):
        if self.mode == "add_wire" and self.start_item:
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(item, SymbolItem) and item is not self.start_item:
                wire = WireItem(self.start_item, item)
                self.addItem(wire)
            self.start_item = None
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # Update live position in properties panel if a symbol is selected
        selected = self.selectedItems()
        if selected and isinstance(selected[0], SymbolItem):
            self.properties_panel.update_properties(selected[0])


class PropertiesPanel(QWidget):
    """Dockable widget showing symbol properties."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.name_label = QLabel("Name:")
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        self.pos_label = QLabel("Position: (x=0, y=0)")
        layout.addWidget(self.pos_label)

        self.setLayout(layout)
        self.current_item = None

        self.name_edit.editingFinished.connect(self.rename_symbol)

    def update_properties(self, item: SymbolItem):
        self.current_item = item
        self.name_edit.setText(item.name)
        pos = item.scenePos()
        self.pos_label.setText(f"Position: (x={int(pos.x())}, y={int(pos.y())})")

    def rename_symbol(self):
        if self.current_item:
            self.current_item.name = self.name_edit.text()


class DiagramEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wiring Diagram Editor (With Properties & Snapping)")
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
