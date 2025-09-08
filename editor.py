import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsScene, QGraphicsView, QDockWidget,
    QWidget, QVBoxLayout, QLabel, QLineEdit, QAction, QToolBar,
    QGraphicsRectItem, QGraphicsPathItem, QColorDialog, QPushButton,QGraphicsSimpleTextItem
)
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt, QPointF, QLineF
from PyQt5.QtWidgets import QGraphicsItem


class SymbolItem(QGraphicsRectItem):
    """Basic rectangle symbol with a name and connected_wires tracking."""
    def __init__(self, x, y, name="Symbol"):
        super().__init__(0, 0, 60, 40)
        self.setPos(x, y)
        self.name = name
        self.connected_wires = []  # wires attached to this symbol

        # Interactivity
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        # Important: allow itemChange to be called when position changes
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        # Draw order (symbols above wires)
        self.setZValue(1)
        self.setBrush(Qt.lightGray)
        self.label = QGraphicsSimpleTextItem(self.name, self)
        self.label.setFlag(QGraphicsItem.ItemIgnoresTransformations)  # keep readable while zooming
        self.label.setPos(self.rect().center().x() - self.label.boundingRect().width()/2,
                          -self.label.boundingRect().height() - 2)

    def get_center(self) -> QPointF:
        """Return center point in scene coordinates."""
        return self.scenePos() + self.rect().center()

    def get_edge_point(self, target_point: QPointF) -> QPointF:
        """
        Given a target point (scene coords), return the nearest point
        on this symbol's rectangle edge (scene coords).
        """
        rect_scene = self.rect().translated(self.scenePos())
        # clamp x,y into rect bounds
        x = min(max(target_point.x(), rect_scene.left()), rect_scene.right())
        y = min(max(target_point.y(), rect_scene.top()), rect_scene.bottom())

        # distances to each edge
        dx_left = abs(target_point.x() - rect_scene.left())
        dx_right = abs(target_point.x() - rect_scene.right())
        dy_top = abs(target_point.y() - rect_scene.top())
        dy_bottom = abs(target_point.y() - rect_scene.bottom())

        min_dist = min(dx_left, dx_right, dy_top, dy_bottom)
        if min_dist == dx_left:
            return QPointF(rect_scene.left(), y)
        elif min_dist == dx_right:
            return QPointF(rect_scene.right(), y)
        elif min_dist == dy_top:
            return QPointF(x, rect_scene.top())
        else:
            return QPointF(x, rect_scene.bottom())

    def itemChange(self, change, value):
        """
        Called when something about the item changes.
        We care about ItemPositionHasChanged so we can update connected wires.
        """
        if change == QGraphicsItem.ItemPositionHasChanged:
            for wire in list(self.connected_wires):
                # update each connected wire path when this symbol moves
                wire.update_path()
        return super().itemChange(change, value)


class WireItem(QGraphicsPathItem):
    """Wire connecting two SymbolItem instances with a simple 90-degree route."""
    def __init__(self, start_item: SymbolItem, end_item: SymbolItem, color=QColor("black")):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.color = QColor(color)

        self.setPen(QPen(self.color, 2))
        self.setFlags(QGraphicsPathItem.ItemIsSelectable | QGraphicsPathItem.ItemIsFocusable)
        # Draw wires under symbols
        self.setZValue(0)

        # Register with the symbols so they can notify us
        start_item.connected_wires.append(self)
        end_item.connected_wires.append(self)

        # Keep the path in scene coordinates; item's pos is left at (0,0)
        self.update_path()

    def update_path(self):
        """Recalculate a 90° path from start->end using side midpoints and offset for parallels."""
        if not (self.start_item and self.end_item):
            return

        # --- helper: get midpoint of closest side ---
        def side_midpoint(symbol: SymbolItem, target: QPointF) -> QPointF:
            rect_scene = symbol.rect().translated(symbol.scenePos())
            # distances to sides
            dx_left = abs(target.x() - rect_scene.left())
            dx_right = abs(target.x() - rect_scene.right())
            dy_top = abs(target.y() - rect_scene.top())
            dy_bottom = abs(target.y() - rect_scene.bottom())
            print(symbol.name,dx_left,dx_right,dy_top,dy_bottom)
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

        # compute start and end points (midpoints of chosen sides)
        start = side_midpoint(self.start_item, self.end_item.get_center())
        end = side_midpoint(self.end_item, self.start_item.get_center())

        # --- offset parallel wires ---
        siblings = [
            w for w in self.start_item.connected_wires
            if (w.start_item is self.start_item and w.end_item is self.end_item) or
               (w.start_item is self.end_item and w.end_item is self.start_item)
        ]
        index = siblings.index(self)
        offset = (index - (len(siblings)-1)/2) * 10  # spread out by 10px

        # build path
        path = QPainterPath()
        path.moveTo(start)

        # horizontal vs vertical preference
        if abs(start.y() - end.y()) < 6:
            # horizontal wire
            path.lineTo(end + QPointF(0, offset))
        elif abs(start.x() - end.x()) < 6:
            # vertical wire
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


class PropertiesPanel(QWidget):
    """Shows & edits properties for the selected SymbolItem or WireItem."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)

        # --- Symbol fields ---
        self.name_label = QLabel("Name:")
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_edit)

        self.pos_label = QLabel("Position: (x=0, y=0)")
        layout.addWidget(self.pos_label)

        layout.addSpacing(10)

        # --- Wire fields ---
        self.start_label = QLabel("Start: -")
        self.end_label = QLabel("End: -")
        layout.addWidget(self.start_label)
        layout.addWidget(self.end_label)

        color_row = QWidget()
        color_layout = QVBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.color_label = QLabel("Color: -")
        self.color_button = QPushButton("Pick Color")
        color_layout.addWidget(self.color_label)
        color_layout.addWidget(self.color_button)
        color_row.setLayout(color_layout)
        layout.addWidget(color_row)

        self.setLayout(layout)

        self.current_item = None

        # Connections
        self.name_edit.editingFinished.connect(self.rename_symbol)
        self.color_button.clicked.connect(self._on_color_button_clicked)

    def clear_properties(self):
        self.current_item = None
        self.name_edit.setText("")
        self.name_edit.setEnabled(False)
        self.pos_label.setText("Position: -")
        self.start_label.setText("Start: -")
        self.end_label.setText("End: -")
        self.color_label.setText("Color: -")
        self.color_button.setEnabled(False)

    def update_properties(self, item):
        """Populate the panel depending on whether a symbol or wire is selected."""
        self.current_item = item

        if isinstance(item, SymbolItem):
            # Symbol editing
            self.name_edit.setEnabled(True)
            self.name_edit.setText(item.name)
            pos = item.scenePos()
            self.pos_label.setText(f"Position: (x={int(pos.x())}, y={int(pos.y())})")

            # Clear wire fields
            self.start_label.setText("Start: -")
            self.end_label.setText("End: -")
            self.color_label.setText("Color: -")
            self.color_button.setEnabled(False)

        elif isinstance(item, WireItem):
            # Wire editing (read-only start/end names, color editable)
            self.name_edit.setEnabled(False)
            self.name_edit.setText("")
            self.pos_label.setText("Position: -")
            self.start_label.setText(f"Start: {item.start_item.name}")
            self.end_label.setText(f"End: {item.end_item.name}")
            self.color_label.setText(f"Color: {item.color.name()}")
            self.color_button.setEnabled(True)

        else:
            self.clear_properties()

    def rename_symbol(self):
        """Apply name change to the currently selected symbol."""
        if isinstance(self.current_item, SymbolItem):
            new_name = self.name_edit.text()
            self.current_item.name = new_name
            self.current_item.label.setText(new_name)
            self.current_item.label.setPos(
                self.current_item.rect().center().x() - self.current_item.label.boundingRect().width()/2,
                -self.current_item.label.boundingRect().height() - 2
            )
            # update any connected wires' displayed labels (if a wire is selected later)
            for w in self.current_item.connected_wires:
                w.update_path()

    def _on_color_button_clicked(self):
        """Open color dialog for currently selected wire (if any)."""
        if isinstance(self.current_item, WireItem):
            initial = self.current_item.color
            color = QColorDialog.getColor(initial, self, "Pick Wire Color")
            if color.isValid():
                self.current_item.set_color(color)
                self.color_label.setText(f"Color: {self.current_item.color.name()}")


class DiagramScene(QGraphicsScene):
    """Scene that supports adding symbols and wires and notifies the properties panel."""
    def __init__(self, properties_panel: PropertiesPanel):
        super().__init__()
        self.mode = "select"   # modes: select | add_symbol | add_wire
        self.start_item = None
        self.properties_panel = properties_panel
        self.symbol_counter = 1

        # react to selection changes (update properties panel)
        self.selectionChanged.connect(self.on_selection_changed)

    def set_mode(self, mode: str):
        self.mode = mode
        # clear any half-finished wire
        self.start_item = None

    def on_selection_changed(self):
        selected = self.selectedItems()
        if selected:
            self.properties_panel.update_properties(selected[0])
        else:
            self.properties_panel.clear_properties()

    def mousePressEvent(self, event):
        if self.mode == "add_symbol":
            pos = event.scenePos()
            name = f"S{self.symbol_counter}"
            self.symbol_counter += 1
            symbol = SymbolItem(pos.x(), pos.y(), name=name)
            self.addItem(symbol)
            # select the new symbol so properties panel updates
            self.clearSelection()
            symbol.setSelected(True)
            self.properties_panel.update_properties(symbol)
            return  # don't pass to base

        elif self.mode == "add_wire":
            item = self.itemAt(event.scenePos(), self.views()[0].transform()) if self.views() else None
            if isinstance(item, SymbolItem):
                self.start_item = item
            else:
                self.start_item = None
            # do not call super yet (we will create wire on release)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.mode == "add_wire" and self.start_item:
            item = self.itemAt(event.scenePos(), self.views()[0].transform()) if self.views() else None
            if isinstance(item, SymbolItem) and item is not self.start_item:
                wire = WireItem(self.start_item, item)
                self.addItem(wire)
                # select the new wire
                self.clearSelection()
                wire.setSelected(True)
                self.properties_panel.update_properties(wire)
            self.start_item = None
        else:
            super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        # If a symbol is selected while being moved, refresh position in properties panel
        selected = self.selectedItems()
        if selected and isinstance(selected[0], SymbolItem):
            self.properties_panel.update_properties(selected[0])


class DiagramEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wiring Diagram Editor (Selectable Wires, Live Update)")
        self.resize(1000, 700)

        # Properties panel (dock)
        self.properties_panel = PropertiesPanel()
        dock = QDockWidget("Properties", self)
        dock.setWidget(self.properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)

        # Scene & View
        self.scene = DiagramScene(self.properties_panel)
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        # Toolbar for modes
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
