import sys
import math
import platform
import time
from PyQt5.QtWidgets import QApplication, QDialog, QGraphicsView, QGraphicsScene, QGraphicsItem
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QPen, QColor, QBrush, QPainterPath, QPainter, QFont, QFontMetrics
import pyautogui
from pynput import mouse

pyautogui.FAILSAFE = False

IS_MACOS = platform.system() == "Darwin"
COMMAND_KEY = "command" if IS_MACOS else "ctrl"
PREVIOUS_KEY = "[" if IS_MACOS else "left"
DELETE_KEY = "delete" if IS_MACOS else "del"

# Configuration options for customization
MENU_SIZE = 300
CENTER_RADIUS = 50
OUTER_RADIUS = 150
SLICE_COLOR = QColor(30, 30, 30, 220)  # Dark Charcoal
SLICE_HOVER_COLOR = QColor(0, 100, 255, 180)  # Neon Blue
BORDER_COLOR = QColor(0, 255, 255, 200)  # Neon Blue
INNER_ELLIPSE_COLOR = QColor(0, 255, 0, 200)  # Neon Green
FONT_FAMILY = "Poppins"
ACTION_FONT_SIZE = 6
SHORTCUT_FONT_SIZE = 5
DEBUG = True

def debug_print(message):
    if DEBUG:
        print(message)

class GlobalMouseTracker(QObject):
    mouse_pressed = pyqtSignal(int, int)
    mouse_released = pyqtSignal(int, int)
    mouse_moved = pyqtSignal(int, int)

    def __init__(self):
        super().__init__()
        self.listener = mouse.Listener(on_click=self.on_click, on_move=self.on_move)
        self.listener.start()

    def on_click(self, x, y, button, pressed):
        if button == mouse.Button.right:
            if pressed:
                self.mouse_pressed.emit(int(x), int(y))
            else:
                self.mouse_released.emit(int(x), int(y))

    def on_move(self, x, y):
        self.mouse_moved.emit(int(x), int(y))

class RadialMenuSlice(QGraphicsItem):
    def __init__(self, center, inner_radius, outer_radius, start_angle, end_angle, color, hover_color, parent=None):
        super().__init__(parent)
        self.center = center
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.color = color
        self.hover_color = hover_color
        self.is_hovered = False
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(self.center.x() - self.outer_radius, self.center.y() - self.outer_radius,
                      self.outer_radius * 2, self.outer_radius * 2)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        start_point = self.center + QPointF(
            self.inner_radius * math.cos(self.start_angle),
            self.inner_radius * math.sin(self.start_angle)
        )
        path.moveTo(start_point)
        path.arcTo(self.boundingRect(), math.degrees(-self.start_angle), math.degrees(self.start_angle - self.end_angle))
        path.arcTo(QRectF(self.center.x() - self.inner_radius, self.center.y() - self.inner_radius,
                          self.inner_radius * 2, self.inner_radius * 2),
                   math.degrees(-self.end_angle), math.degrees(self.end_angle - self.start_angle))
        path.closeSubpath()
        painter.setBrush(self.hover_color if self.is_hovered else self.color)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

        if self.is_hovered:
            painter.setPen(QPen(BORDER_COLOR, 2))
            painter.drawPath(path)
            painter.setBrush(QBrush(INNER_ELLIPSE_COLOR))
            painter.drawEllipse(self.center, self.inner_radius - 5, self.inner_radius - 5)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()

class RadialMenu(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.setFixedSize(MENU_SIZE, MENU_SIZE)

        self.view = QGraphicsView(self)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setFixedSize(MENU_SIZE, MENU_SIZE)

        self.scene = QGraphicsScene(0, 0, MENU_SIZE, MENU_SIZE)
        self.view.setScene(self.scene)

        self.actions = []

        self.slices = []
        self.texts = []
        self.selected = None
        self.center_item = None

    def draw_menu(self):
        self.scene.clear()
        self.slices = []
        self.texts = []

        center = QPointF(MENU_SIZE / 2, MENU_SIZE / 2)
        start_angle = -math.pi / 2

        for i, (action, _, shortcut) in enumerate(self.actions):
            end_angle = start_angle - 2 * math.pi / len(self.actions)
            slice_item = RadialMenuSlice(
                center, CENTER_RADIUS, OUTER_RADIUS,
                start_angle, end_angle,
                SLICE_COLOR, SLICE_HOVER_COLOR
            )
            self.scene.addItem(slice_item)
            self.slices.append(slice_item)

            text_angle = (start_angle + end_angle) / 2
            text_radius = (CENTER_RADIUS + OUTER_RADIUS) / 2
            text_pos = center + QPointF(text_radius * math.cos(text_angle), text_radius * math.sin(text_angle))

            text_item = self.create_text_item(f"{action}", ACTION_FONT_SIZE, Qt.white, text_pos, 50)
            self.texts.append(text_item)

            shortcut_item = self.create_text_item(f"{shortcut}", SHORTCUT_FONT_SIZE, Qt.lightGray, text_pos, 50, adjust_y=text_item.boundingRect().height() / 2)
            self.texts.append(shortcut_item)

            start_angle = end_angle

        self.center_item = self.scene.addEllipse(
            center.x() - CENTER_RADIUS, center.y() - CENTER_RADIUS,
            CENTER_RADIUS * 2, CENTER_RADIUS * 2,
            QPen(Qt.NoPen), QBrush(QColor(0, 0, 0, 200))
        )

    def create_text_item(self, text, font_size, color, position, max_width=60, adjust_y=0):
        font = QFont(FONT_FAMILY, font_size, QFont.Bold if font_size == ACTION_FONT_SIZE else QFont.Normal)
        text_item = self.scene.addText("")
        text_item.setDefaultTextColor(color)
        text_item.setFont(font)
        self.wrap_text_item(text_item, text, max_width)
        text_item.setPos(position.x() - text_item.boundingRect().width() / 2,
                         position.y() - text_item.boundingRect().height() / 2 + adjust_y)
        text_item.setToolTip(text)
        return text_item

    def wrap_text_item(self, text_item, text, max_width=60):
        font_metrics = QFontMetrics(text_item.font())
        wrapped_text = ""
        for line in text.split('\n'):
            wrapped_line = ""
            for word in line.split():
                test_line = wrapped_line + ("" if not wrapped_line else " ") + word
                if font_metrics.width(test_line) > max_width:
                    wrapped_text += wrapped_line + "\n"
                    wrapped_line = word
                else:
                    wrapped_line = test_line
            wrapped_text += wrapped_line + "\n"
        text_item.setPlainText(wrapped_text.strip())

    def update_selection(self, pos):
        center = QPointF(MENU_SIZE / 2, MENU_SIZE / 2)
        vector = pos - center
        distance = (vector.x()**2 + vector.y()**2)**0.5

        if distance < CENTER_RADIUS:
            self.selected = None
            self.update_visuals()
            return

        angle = math.atan2(-vector.y(), vector.x())
        if angle < 0:
            angle += 2 * math.pi

        index = int(len(self.actions) * angle / (2 * math.pi))
        index = (index - 2) % len(self.actions)

        if self.selected != index:
            self.selected = index
            self.update_visuals()
            debug_print(f"Selection updated: {self.actions[self.selected][0]}")

    def update_visuals(self):
        for i, slice_item in enumerate(self.slices):
            slice_item.is_hovered = (i == self.selected)
            slice_item.update()

        self.center_item.setBrush(QBrush(SLICE_HOVER_COLOR if self.selected is not None else QColor(0, 0, 0, 200)))

    def show_at(self, x, y):
        self.move(int(x) - MENU_SIZE // 2, int(y) - MENU_SIZE // 2)
        QTimer.singleShot(0, self.show)

    def get_selected_action(self):
        if self.selected is not None:
            debug_print(f"Action selected: {self.actions[self.selected][0]}")
            return self.actions[self.selected][1]
        debug_print("No action selected")
        return None

    def add_action(self, action_name, action_function, shortcut):
        self.actions.append((action_name, action_function, shortcut))
        self.draw_menu()

    def remove_action(self, action_name):
        self.actions = [action for action in self.actions if action[0] != action_name]
        self.draw_menu()

    def reorder_actions(self, new_order):
        reordered_actions = [self.actions[i] for i in new_order]
        self.actions = reordered_actions
        self.draw_menu()

    def select_all(self):
        self.perform_keystroke('a')

    def copy(self):
        self.perform_keystroke('c')

    def select_all_and_copy(self):
        self.select_all()
        QTimer.singleShot(100, self.copy)

    def paste(self):
        self.perform_keystroke('v')

    def cut(self):
        self.perform_keystroke('x')

    def delete(self):
        pyautogui.press(DELETE_KEY)

    def next(self):
        pyautogui.hotkey('alt', 'right')

    def previous(self):
        if IS_MACOS:
            pyautogui.keyDown(COMMAND_KEY)
            time.sleep(0.1)
            pyautogui.press(PREVIOUS_KEY)
            pyautogui.keyUp(COMMAND_KEY)
        else:
            pyautogui.hotkey('alt', PREVIOUS_KEY)

    def undo(self):
        self.perform_keystroke('z')

    def redo(self):
        if IS_MACOS:
            pyautogui.keyDown(COMMAND_KEY)
            pyautogui.keyDown('shift')
            time.sleep(0.1)
            pyautogui.press('z')
            pyautogui.keyUp('shift')
            pyautogui.keyUp(COMMAND_KEY)
        else:
            self.perform_keystroke('y')

    def perform_keystroke(self, key):
        pyautogui.keyDown(COMMAND_KEY)
        time.sleep(0.1)
        pyautogui.press(key)
        pyautogui.keyUp(COMMAND_KEY)
        debug_print(f"Executing: {key.upper()}")

class EnhancedRightClick(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.radial_menu = RadialMenu()
        self.mouse_tracker = GlobalMouseTracker()
        self.right_click_start = None
        self.is_dragging = False
        self.hold_timer = QTimer()
        self.hold_timer.setSingleShot(True)
        self.hold_threshold = 200  # 200 ms hold threshold

        self.mouse_tracker.mouse_pressed.connect(self.on_mouse_pressed)
        self.mouse_tracker.mouse_released.connect(self.on_mouse_released)
        self.mouse_tracker.mouse_moved.connect(self.on_mouse_moved)
        self.hold_timer.timeout.connect(self.on_hold_timeout)

    def start(self):
        debug_print(f"Enhanced Right-Click application started on {'macOS' if IS_MACOS else 'Windows'}")
        sys.exit(self.app.exec_())

    def on_mouse_pressed(self, x, y):
        debug_print(f"Mouse pressed at ({x}, {y})")
        self.right_click_start = (x, y)
        self.hold_timer.start(self.hold_threshold)

    def on_mouse_released(self, x, y):
        debug_print(f"Mouse released at ({x}, {y})")
        self.hold_timer.stop()
        if self.radial_menu.isVisible():
            action = self.radial_menu.get_selected_action()
            self.radial_menu.hide()
            if action:
                QTimer.singleShot(10, action)
        self.right_click_start = None
        self.is_dragging = False

    def on_mouse_moved(self, x, y):
        if self.is_dragging and self.radial_menu.isVisible():
            local_x = x - self.right_click_start[0] + MENU_SIZE // 2
            local_y = y - self.right_click_start[1] + MENU_SIZE // 2
            self.radial_menu.update_selection(QPointF(local_x, local_y))

    def on_hold_timeout(self):
        if self.right_click_start:
            x, y = self.right_click_start
            self.is_dragging = True
            self.radial_menu.show_at(x, y)

if __name__ == "__main__":
    debug_print(f"Starting Enhanced Right-Click application on {'macOS' if IS_MACOS else 'Windows'}")
    app = EnhancedRightClick()
    app.radial_menu.add_action("Select All + Copy", app.radial_menu.select_all_and_copy, "Ctrl+A + Ctrl+C")
    app.radial_menu.add_action("Redo", app.radial_menu.redo, "Ctrl+Y")
    app.radial_menu.add_action("Next", app.radial_menu.next, "Alt+→")
    app.radial_menu.add_action("Copy", app.radial_menu.copy, "Ctrl+C")
    app.radial_menu.add_action("Paste", app.radial_menu.paste, "Ctrl+V")
    app.radial_menu.add_action("Cut", app.radial_menu.cut, "Ctrl+X")
    app.radial_menu.add_action("Undo", app.radial_menu.undo, "Ctrl+Z")
    app.radial_menu.add_action("Select All", app.radial_menu.select_all, "Ctrl+A")
    app.start()
