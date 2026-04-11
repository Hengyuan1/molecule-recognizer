"""Fullscreen overlay for capturing a screen region."""

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget


class ScreenshotOverlay(QWidget):
    """Semi-transparent fullscreen overlay.

    The user draws a rectangle by clicking and dragging.
    On mouse release the captured region is emitted as a QPixmap signal.
    Press Escape to cancel.
    """

    captured = Signal(QPixmap)  # emitted with the cropped screenshot
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._origin = QPoint()
        self._current = QPoint()
        self._selecting = False
        self._full_screenshot: QPixmap | None = None

    def start(self):
        """Grab the entire screen, then show the overlay for region selection."""
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.cancelled.emit()
            return
        self._full_screenshot = screen.grabWindow(0)
        geo = screen.geometry()
        self.setGeometry(geo)
        self.showFullScreen()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Draw the screenshot as background
        if self._full_screenshot:
            painter.drawPixmap(0, 0, self._full_screenshot)
        # Semi-transparent dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self._selecting:
            rect = QRect(self._origin, self._current).normalized()
            # Clear the selection area (show original screenshot)
            if self._full_screenshot:
                painter.drawPixmap(rect, self._full_screenshot, rect)
            # Draw selection border
            pen = QPen(QColor(0, 120, 215), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._current = event.pos()
            self._selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._selecting:
            self._current = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._selecting:
            self._selecting = False
            rect = QRect(self._origin, self._current).normalized()
            self.hide()
            if rect.width() > 5 and rect.height() > 5 and self._full_screenshot:
                cropped = self._full_screenshot.copy(rect)
                self.captured.emit(cropped)
            else:
                self.cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._selecting = False
            self.hide()
            self.cancelled.emit()
