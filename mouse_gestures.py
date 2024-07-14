import sys
import math
import platform
import time
from PyQt5.QtWidgets import QApplication, QDialog, QGraphicsView, QGraphicsScene, QGraphicsItem, QVBoxLayout, QPushButton, QTextEdit, QGraphicsPixmapItem
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal, QObject, QEvent, QPropertyAnimation
from PyQt5.QtGui import QPen, QColor, QBrush, QPainterPath, QPainter, QFont, QPixmap
import pyautogui
from pynput import mouse

# Disable PyAutoGUI fail-safe
pyautogui.FAILSAFE = False

# Detect the operating system
IS_MACOS = platform.system() == "Darwin"

# Define key mappings based on the OS
COMMAND_KEY = "command" if IS_MACOS else "ctrl"
PREVIOUS_KEY = "[" if IS_MACOS else "left"
DELETE_KEY = "delete" if IS_MACOS else "del"

# Debug mode for logging
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
        self.listener = mouse.Listener(
            on_click=self.on_click,
            on_move=self.on_move)
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
        path.moveTo(self.center + QPointF(self.inner_radius * math.cos(self.start_angle),
                                          self.inner_radius * math.sin(self.start_angle)))
        path.arcTo(self.boundingRect(), math.degrees(-self.start_angle), math.degrees(self.start_angle - self.end_angle))
        path.arcTo(QRectF(self.center.x() - self.inner_radius, self.center.y() - self.inner_radius,
                          self.inner_radius * 2, self.inner_radius * 2),
                   math.degrees(-self.end_angle), math.degrees(self.end_angle - self.start_angle))
        path.closeSubpath()

        painter.setBrush(self.hover_color if self.is_hovered else self.color)
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()

class RadialMenu(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 300)

        self.view = QGraphicsView(self)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setStyleSheet("background: transparent;")
        self.view.setFixedSize(300, 300)

        self.scene = QGraphicsScene(0, 0, 300, 300)
        self.view.setScene(self.scene)

        cmd_key = "⌘" if IS_MACOS else "Ctrl+"
        self.actions = [
            ("Select All + Copy", self.select_all_and_copy, f"{cmd_key}A + {cmd_key}C", "icons/select_all_copy.png"),
            ("Redo", self.redo, f"{cmd_key}Y" if not IS_MACOS else "⇧{cmd_key}Z", "icons/redo.png"),
            ("Next", self.next, "Alt+→", "icons/next.png"),
            ("Copy", self.copy, f"{cmd_key}C", "icons/copy.png"),
            ("Paste", self.paste, f"{cmd_key}V", "icons/paste.png"),
            ("Cut", self.cut, f"{cmd_key}X", "icons/cut.png"),
            ("Previous", self.previous, f"{cmd_key}[" if IS_MACOS else "Alt+←", "icons/previous.png"),
            ("Undo", self.undo, f"{cmd_key}Z", "icons/undo.png"),
            ("Select All", self.select_all, f"{cmd_key}A", "icons/select_all.png")
        ]

        self.slices = []
        self.texts = []
        self.icons = []
        self.selected = None
        self.center_item = None
        self.draw_menu()

    def draw_menu(self):
        center = QPointF(150, 150)
        outer_radius = 120
        inner_radius = 40
        start_angle = -math.pi / 2

        for i, (action, _, shortcut, icon_path) in enumerate(self.actions):
            end_angle = start_angle - 2 * math.pi / len(self.actions)
            color = QColor(60, 60, 60, 180)
            hover_color = QColor(100, 100, 255, 180)
            
            slice_item = RadialMenuSlice(center, inner_radius, outer_radius, start_angle, end_angle, color, hover_color)
            self.scene.addItem(slice_item)
            self.slices.append(slice_item)

            text_angle = (start_angle + end_angle) / 2
            text_radius = (inner_radius + outer_radius) / 2
            text_pos = center + QPointF(text_radius * math.cos(text_angle), text_radius * math.sin(text_angle))

            text_item = self.scene.addText(f"{action}\n{shortcut}")
            text_item.setDefaultTextColor(Qt.white)
            text_item.setFont(QFont("Arial", 8, QFont.Bold))
            text_item.setPos(text_pos.x() - text_item.boundingRect().width() / 2,
                             text_pos.y() - text_item.boundingRect().height() / 2)
            self.texts.append(text_item)

            icon_item = QGraphicsPixmapItem(QPixmap(icon_path))
            icon_item.setPos(text_pos.x() - 20, text_pos.y() - 40)  # Adjust position
            self.scene.addItem(icon_item)
            self.icons.append(icon_item)

            start_angle = end_angle

        # Add center circle
        self.center_item = self.scene.addEllipse(center.x() - inner_radius, center.y() - inner_radius,
                                                 inner_radius * 2, inner_radius * 2,
                                                 QPen(Qt.NoPen), QBrush(QColor(30, 30, 30, 200)))

    def update_selection(self, pos):
        center = QPointF(150, 150)
        vector = pos - center
        distance = (vector.x()**2 + vector.y()**2)**0.5
        
        if distance < 40:  # Dead zone
            self.selected = None
            self.update_visuals()
            return

        angle = math.atan2(-vector.y(), vector.x())
        if angle < 0:
            angle += 2 * math.pi

        index = int(len(self.actions) * angle / (2 * math.pi))
        index = (index - 2) % len(self.actions)  # Adjust for starting at 12 o'clock position
        
        if self.selected != index:
            self.selected = index
            self.update_visuals()
            debug_print(f"Selection updated: {self.actions[self.selected][0]}")

    def update_visuals(self):
        for i, slice_item in enumerate(self.slices):
            slice_item.is_hovered = (i == self.selected)
            slice_item.update()

        self.center_item.setBrush(QBrush(QColor(100, 100, 255, 200) if self.selected is not None else QColor(30, 30, 30, 200)))

    def show_at(self, x, y):
        self.move(int(x) - 150, int(y) - 150)
        QTimer.singleShot(0, self.show)

    def get_selected_action(self):
        if self.selected is not None:
            debug_print(f"Action selected: {self.actions[self.selected][0]}")
            return self.actions[self.selected][1]
        debug_print("No action selected")
        return None

    def select_all(self):
        debug_print("Executing: Select All")
        pyautogui.keyDown(COMMAND_KEY)
        time.sleep(0.1)
        pyautogui.press('a')
        pyautogui.keyUp(COMMAND_KEY)

    def copy(self):
        debug_print("Executing: Copy")
        pyautogui.keyDown(COMMAND_KEY)
        time.sleep(0.1)
        pyautogui.press('c')
        pyautogui.keyUp(COMMAND_KEY)

    def select_all_and_copy(self):
        debug_print("Executing: Select All + Copy")
        self.select_all()
        QTimer.singleShot(100, self.copy)  # Add a small delay to ensure the select all completes

    def paste(self):
        debug_print("Executing: Paste")
        pyautogui.keyDown(COMMAND_KEY)
        time.sleep(0.1)
        pyautogui.press('v')
        pyautogui.keyUp(COMMAND_KEY)

    def cut(self):
        debug_print("Executing: Cut")
        pyautogui.keyDown(COMMAND_KEY)
        time.sleep(0.1)
        pyautogui.press('x')
        pyautogui.keyUp(COMMAND_KEY)

    def delete(self):
        debug_print("Executing: Delete")
        pyautogui.press(DELETE_KEY)

    def next(self):
        debug_print("Executing: Next")
        pyautogui.hotkey('alt', 'right')

    def previous(self):
        debug_print("Executing: Previous")
        if IS_MACOS:
            pyautogui.keyDown(COMMAND_KEY)
            time.sleep(0.1)
            pyautogui.press(PREVIOUS_KEY)
            pyautogui.keyUp(COMMAND_KEY)
        else:
            pyautogui.hotkey('alt', PREVIOUS_KEY)

    def undo(self):
        debug_print("Executing: Undo")
        pyautogui.keyDown(COMMAND_KEY)
        time.sleep(0.1)
        pyautogui.press('z')
        pyautogui.keyUp(COMMAND_KEY)

    def redo(self):
        debug_print("Executing: Redo")
        if IS_MACOS:
            pyautogui.keyDown(COMMAND_KEY)
            pyautogui.keyDown('shift')
            time.sleep(0.1)
            pyautogui.press('z')
            pyautogui.keyUp('shift')
            pyautogui.keyUp(COMMAND_KEY)
        else:
            pyautogui.keyDown(COMMAND_KEY)
            time.sleep(0.1)
            pyautogui.press('y')
            pyautogui.keyUp(COMMAND_KEY)

class EnhancedRightClick(QObject):
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.radial_menu = RadialMenu()
        self.mouse_tracker = GlobalMouseTracker()
        self.right_click_start = None
        self.is_dragging = False

        self.mouse_tracker.mouse_pressed.connect(self.on_mouse_pressed)
        self.mouse_tracker.mouse_released.connect(self.on_mouse_released)
        self.mouse_tracker.mouse_moved.connect(self.on_mouse_moved)

    def start(self):
        debug_print(f"Enhanced Right-Click application started on {'macOS' if IS_MACOS else 'Windows'}")
        sys.exit(self.app.exec_())

    def on_mouse_pressed(self, x, y):
        debug_print(f"Mouse pressed at ({x}, {y})")
        if not self.radial_menu.isVisible():
            self.right_click_start = (x, y)
            self.is_dragging = True
            debug_print("Showing radial menu")
            QTimer.singleShot(10, lambda: self.radial_menu.show_at(x, y))

    def on_mouse_released(self, x, y):
        debug_print(f"Mouse released at ({x}, {y})")
        if self.radial_menu.isVisible():
            action = self.radial_menu.get_selected_action()
            self.radial_menu.hide()
            debug_print("Radial menu hidden")
            if action:
                debug_print("Executing selected action")
                QTimer.singleShot(10, action)
            else:
                debug_print("No action to execute")
            self.right_click_start = None
            self.is_dragging = False

    def on_mouse_moved(self, x, y):
        if self.is_dragging and self.radial_menu.isVisible():
            local_x = x - self.right_click_start[0] + 150
            local_y = y - self.right_click_start[1] + 150
            self.radial_menu.update_selection(QPointF(local_x, local_y))

if __name__ == "__main__":
    debug_print(f"Starting Enhanced Right-Click application on {'macOS' if IS_MACOS else 'Windows'}")
    app = EnhancedRightClick()
    app.start()
