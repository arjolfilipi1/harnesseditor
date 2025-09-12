import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView,
    QGraphicsRectItem, QGraphicsPathItem, QGraphicsItem,
    QAction, QListWidget, QDockWidget
)
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt, QPointF


# ---------------- Base Command ----------------
class Command:
    def undo(self): pass
    def redo(self): pass


# ---------------- Symbol ----------------
class SymbolItem(QGraphicsRectItem):
    counter = 1

    def __init__(self):
        super().__init__(-30, -20, 60, 40)
        self.setFlags(
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemIsMovable
        )
        self.setBrush(Qt.lightGray)

        self.name = f"Symbol{SymbolItem.counter}"
        SymbolItem.counter += 1

        from PyQt5.QtWidgets import QGraphicsSimpleTextItem
        self.label = QGraphicsSimpleTextItem(self.name, self)
        self.label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.update_label_pos()

        self.connected_wires = []

    def update_label_pos(self):
        self.label.setPos(
            self.rect().center().x() - self.label.boundingRect().width()/2,
            -self.label.boundingRect().height() - 2
        )

    def get_center(self):
        return self.scenePos() + self.rect().center()

    def item_type(self):
        return "Symbol"

    def __str__(self):
        return self.name


# ---------------- Wire ----------------
class WireItem(QGraphicsPathItem):
    counter = 1

    def __init__(self, start_item, end_item, color=Qt.black):
        super().__init__()
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setPen(QPen(color, 2))

        self.start_item = start_item
        self.end_item = end_item
        self.color = QColor(color)

        self.name = f"Wire{WireItem.counter}"
        WireItem.counter += 1

        start_item.connected_wires.append(self)
        end_item.connected_wires.append(self)

        self.update_path()

    def update_path(self):
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
        offset = (index - (len(siblings)-1)/2) * 10

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

    def set_color(self, color):
        self.color = QColor(color)
        self.setPen(QPen(self.color, 2))

    def item_type(self):
        return "Wire"

    def __str__(self):
        return self.name


# ---------------- Commands ----------------
class AddSymbolCommand(Command):
    def __init__(self, scene, editor, symbol):
        self.scene = scene
        self.editor = editor
        self.symbol = symbol

    def undo(self):
        self.scene.removeItem(self.symbol)
        self.editor.refresh_list()

    def redo(self):
        self.scene.addItem(self.symbol)
        self.editor.refresh_list()


class AddWireCommand(Command):
    def __init__(self, scene, editor, wire):
        self.scene = scene
        self.editor = editor
        self.wire = wire

    def undo(self):
        self.scene.removeItem(self.wire)
        self.editor.refresh_list()

    def redo(self):
        self.scene.addItem(self.wire)
        self.editor.refresh_list()


# ---------------- Main Editor ----------------
class DiagramEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wiring Diagram Editor")
        self.resize(1000, 600)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        self.undo_stack = []
        self.redo_stack = []

        self.init_ui()
        self.create_list_dock()

    def init_ui(self):
        add_symbol_action = QAction("Add Symbol", self)
        add_symbol_action.triggered.connect(self.add_symbol)
        self.toolbar = self.addToolBar("Tools")
        self.toolbar.addAction(add_symbol_action)

        add_wire_action = QAction("Add Wire", self)
        add_wire_action.triggered.connect(self.add_wire)
        self.toolbar.addAction(add_wire_action)

        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        self.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        self.addAction(redo_action)

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

    def add_symbol(self):
        symbol = SymbolItem()
        symbol.setPos(len(self.scene.items()) * 20, len(self.scene.items()) * 20)
        cmd = AddSymbolCommand(self.scene, self, symbol)
        self.push_command(cmd)

    def add_wire(self):
        selected = [item for item in self.scene.selectedItems() if isinstance(item, SymbolItem)]
        if len(selected) == 2:
            wire = WireItem(selected[0], selected[1])
            cmd = AddWireCommand(self.scene, self, wire)
            self.push_command(cmd)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = DiagramEditor()
    editor.show()
    sys.exit(app.exec_())
