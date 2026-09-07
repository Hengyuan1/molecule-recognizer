"""Place auxiliary windows relative to their owner, never the mouse cursor."""

from PySide6.QtCore import QEvent, QMargins, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout,
)

from .screenshot import is_wsl


def owner_screen(owner):
    """Prefer the screen containing most of the main window (also mid-drag)."""
    fallback = owner.screen()
    # Wayland does not expose reliable global window coordinates. Its window
    # manager uses the native transient-parent relationship instead.
    if QApplication.platformName().startswith("wayland"):
        return fallback
    best, best_area = fallback, 0
    for screen in QApplication.screens():
        overlap = owner.frameGeometry().intersected(screen.geometry())
        area = max(0, overlap.width()) * max(0, overlap.height())
        if area > best_area:
            best, best_area = screen, area
    return best


def centered_geometry(owner: QRect, size: QSize, available: QRect) -> QRect:
    """Center a frame over its owner, clamping to one monitor's work area."""
    width = min(size.width(), available.width())
    height = min(size.height(), available.height())
    x = owner.x() + (owner.width() - width) // 2
    y = owner.y() + (owner.height() - height) // 2
    x = max(available.x(), min(x, available.x() + available.width() - width))
    y = max(available.y(), min(y, available.y() + available.height() - height))
    return QRect(x, y, width, height)


class OwnerDialog(QDialog):
    """Native owned dialog, or an ordinary child-widget review panel on WSLg.

    WSLg can desynchronize native transient frames when closing/repositioning
    dialogs. The WSL panel shares the owner's surface: no winId(), native
    modality, external HWND moves or nested event loop are involved.
    """

    def __init__(self, parent=None):
        owner = parent.window() if parent is not None else None
        embedded = owner is not None and is_wsl()
        super().__init__(owner, Qt.WindowType.Widget if embedded else Qt.WindowType.Dialog)
        self._owner = owner
        self._embedded = embedded
        self._panel_host = None
        self._previous_focus = None
        self._changing_visibility = False
        if embedded:
            self.setWindowFlags(Qt.WindowType.Widget)

    def _create_panel(self):
        central = getattr(self._owner, 'centralWidget', lambda: None)()
        # Inherit the central content's per-monitor font and stylesheet.
        host = QFrame(central if central is not None else self._owner)
        host.setObjectName("owner_dialog_panel")
        host.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        host.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation)
        host.setStyleSheet("QFrame#owner_dialog_panel { background: #e8eef5; }"
                          "QLabel#owner_dialog_title { font-weight: bold; }")
        column = QVBoxLayout(host)
        column.setContentsMargins(12, 12, 12, 12)
        header = QHBoxLayout()
        title = QLabel(self.windowTitle())
        title.setObjectName('owner_dialog_title')
        self._panel_title = title
        header.addWidget(title, 1)
        close = QPushButton("Close")
        self._panel_close = close
        close.setAutoDefault(False)
        close.clicked.connect(self.reject)
        header.addWidget(close)
        column.addLayout(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Scrolling keeps every button accessible even if the owner becomes
        # smaller after a monitor/scale change. No minimum-size propagation
        # from this panel is allowed to grow the main window.
        scroll.setWidget(self)
        column.addWidget(scroll, 1)
        self._panel_host = host
        self.destroyed.connect(host.deleteLater)

    def _sync_panel_font(self):
        # Qt stylesheet widgets don't reliably inherit later setFont changes.
        # Apply the owner's current scale explicitly, including the header.
        font = self._panel_host.parentWidget().font()
        for widget in (self._panel_host, self, self._panel_title, self._panel_close):
            widget.setFont(font)

    def open(self):
        if self._embedded:
            self.setWindowModality(Qt.WindowModality.NonModal)
            self.show()
        else:
            super().open()

    def setVisible(self, visible):  # noqa: N802
        if self._embedded:
            # setWidget/reparenting and showing ancestors also call setVisible.
            # Those internal calls must not create another hosting panel.
            if self._changing_visibility:
                super().setVisible(visible)
                return
            self._changing_visibility = True
            try:
                self._set_panel_visible(visible)
            finally:
                self._changing_visibility = False
            return
        if visible and not self.isVisible() and self.parentWidget() is not None:
            owner = self.parentWidget().window()
            screen = owner_screen(owner)
            self.setScreen(screen)
            # QDialog establishes transient ownership itself when shown.
            # Do not force early native window creation with winId().
            if self.layout() is not None:
                self.layout().activate()
            if not QApplication.platformName().startswith("wayland"):
                handle = self.windowHandle()
                margins = handle.frameMargins() if handle is not None else QMargins()
                frame_size = self.size() + QSize(
                    margins.left() + margins.right(), margins.top() + margins.bottom())
                target = centered_geometry(owner.frameGeometry(), frame_size,
                                           screen.availableGeometry())
                self.resize(target.width() - margins.left() - margins.right(),
                            target.height() - margins.top() - margins.bottom())
                self.move(target.topLeft())
        super().setVisible(visible)

    def _set_panel_visible(self, visible):
        if visible and not self.isVisible():
            self.setWindowModality(Qt.WindowModality.NonModal)
            self._previous_focus = QApplication.focusWidget()
            if self._panel_host is None:
                self._create_panel()
            self._sync_panel_font()
            self._panel_host.setGeometry(self._panel_host.parentWidget().rect())
            self._panel_host.show()
            self._panel_host.raise_()
            QApplication.instance().installEventFilter(self)
            super().setVisible(True)
            self.setFocus(Qt.FocusReason.OtherFocusReason)
        elif not visible:
            super().setVisible(False)
            QApplication.instance().removeEventFilter(self)
            if self._panel_host is not None:
                self._panel_host.hide()
            try:
                if self._previous_focus is not None and self._previous_focus.isVisible():
                    self._previous_focus.setFocus(Qt.FocusReason.OtherFocusReason)
            except RuntimeError:
                pass  # The focused widget may have been deleted meanwhile.
            self._previous_focus = None
            self._owner.update()

    def eventFilter(self, watched, event):  # noqa: N802
        if self._panel_host is None or not self._panel_host.isVisible():
            return False
        if watched is self._panel_host.parentWidget() and event.type() == QEvent.Type.Resize:
            self._panel_host.setGeometry(watched.rect())
        if watched is self._panel_host.parentWidget() and event.type() == QEvent.Type.FontChange:
            self._sync_panel_font()
        kind = event.type()
        if kind not in (
            QEvent.Type.Shortcut, QEvent.Type.KeyPress, QEvent.Type.KeyRelease,
            QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseButtonDblClick, QEvent.Type.Wheel,
        ):
            return False
        # The covering panel handles pointer input. Also block main-window
        # shortcuts and stale focus events, without disabling the main HWND
        # (which can leave it stuck disabled in WSLg). Native title-bar close
        # events and shortcuts in other application windows remain untouched.
        inside = False
        obj = watched
        while obj is not None and obj is not self._owner:
            inside |= obj is self._panel_host
            obj = obj.parent()
        if obj is not self._owner:
            return False
        if kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.reject()
            return True
        if kind == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            forward = (event.key() == Qt.Key.Key_Tab
                       and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            # The panel isn't a native modal window, so explicitly keep Tab
            # traversal inside it rather than focusing the covered editor.
            start = QApplication.focusWidget() or self
            target = start
            while True:
                target = target.nextInFocusChain() if forward else target.previousInFocusChain()
                if (self._panel_host.isAncestorOf(target) and target.isVisible()
                        and target.isEnabled() and target.focusPolicy() & Qt.FocusPolicy.TabFocus):
                    target.setFocus(Qt.FocusReason.TabFocusReason if forward
                                    else Qt.FocusReason.BacktabFocusReason)
                    break
                if target is start:
                    break
            return True
        return not inside
