"""Menu-bar dropdowns painted as child widgets, without native popup grabs."""

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)
from shiboken6 import isValid


class MenuDefinition:
    def __init__(self, title, owner):
        self.title = title
        self.owner = owner
        self._actions = []

    def addAction(self, action):
        self._actions.append(action)
        return action

    def addSeparator(self):
        action = QAction(self.owner)
        action.setSeparator(True)
        return self.addAction(action)

    def actions(self):
        return list(self._actions)


class InlineMenuBar(QWidget):
    """A single in-window dropdown shared by File/Edit/Build/View/Help.

    No QMenu, Qt.Popup, native window handle, cursor polling, or mouse grab is
    used. Switching headings only replaces the contents of this child panel.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("inline_menu_bar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self._menus = []
        self._headings = []
        self._rows = []
        self._current = None
        self._previous_focus = None
        self._eat_release = False
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(10, 4, 10, 4)
        self._layout.setSpacing(0)
        self._layout.addStretch()

        self._panel = QFrame(parent)
        self._panel.setObjectName("inline_menu_panel")
        self._panel.hide()
        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(3, 3, 3, 3)
        self._scroll = QScrollArea(self._panel)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        panel_layout.addWidget(self._scroll)
        self._contents = QWidget()
        self._contents.setObjectName("inline_menu_contents")
        self._rows_layout = QVBoxLayout(self._contents)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._scroll.setWidget(self._contents)
        QApplication.instance().installEventFilter(self)

    def addMenu(self, title):
        menu = MenuDefinition(title, self)
        index = len(self._menus)
        self._menus.append(menu)
        button = QPushButton(title, self)  # Includes standard Alt+letter mnemonic.
        button.setObjectName("inline_menu_heading")
        button.setCheckable(True)
        button.setMouseTracking(True)
        button.clicked.connect(lambda checked=False, i=index: self._toggle(i))
        self._headings.append(button)
        self._layout.insertWidget(index, button)
        return menu

    def _toggle(self, index):
        if self._current == index:
            self.close_menu()
        else:
            self.open_menu(index)

    def open_menu(self, index):
        if self._current is None:
            self._previous_focus = QApplication.focusWidget()
        self._current = index
        for i, button in enumerate(self._headings):
            button.setChecked(i == index)
        while self._rows_layout.count():
            widget = self._rows_layout.takeAt(0).widget()
            widget.hide()
            widget.deleteLater()
        self._rows = []
        for action in self._menus[index].actions():
            if not action.isVisible():
                continue
            if action.isSeparator():
                separator = QFrame()
                separator.setObjectName("inline_menu_separator")
                separator.setFixedHeight(1)
                self._rows_layout.addWidget(separator)
                separator.show()
                continue
            row = QPushButton()
            row.setObjectName("inline_menu_item")
            text = action.text()
            if not action.shortcut().isEmpty():
                text += "    " + action.shortcut().toString()
            row.setText(text)
            row.setIcon(action.icon())
            row.setEnabled(action.isEnabled())
            row.setAccessibleName(action.text())
            row.clicked.connect(lambda checked=False, a=action: self._activate(a))
            self._rows_layout.addWidget(row)
            row.show()
            self._rows.append(row)
        self._contents.ensurePolished()
        self._rows_layout.activate()
        hint = self._rows_layout.sizeHint()
        self._panel.ensurePolished()
        frame_margins = self._panel.contentsMargins()
        layout_margins = self._panel.layout().contentsMargins()
        vertical_padding = (frame_margins.top() + frame_margins.bottom()
                            + layout_margins.top() + layout_margins.bottom())
        available = self.parentWidget().rect()
        anchor = self._headings[index].mapTo(self.parentWidget(),
                                            QPoint(0, self._headings[index].height()))
        width = min(available.width(), hint.width() + 28)
        height = min(max(1, available.height() - anchor.y()),
                     hint.height() + vertical_padding)
        self._panel.setGeometry(max(0, min(anchor.x(), available.width() - width)),
                                anchor.y(), width, height)
        self._panel.show()
        self._panel.raise_()
        self._scroll.verticalScrollBar().setValue(0)
        self._focus_row(0)

    def close_menu(self, restore_focus=True):
        self._eat_release = False
        self._panel.hide()
        self._current = None
        for button in self._headings:
            button.setChecked(False)
        previous, self._previous_focus = self._previous_focus, None
        if (restore_focus and previous is not None and isValid(previous)
                and previous.isVisible() and previous.isEnabled()):
            previous.setFocus()

    def _activate(self, action):
        self.close_menu()
        if action.isEnabled() and action.isVisible():
            action.trigger()

    def _focus_row(self, index):
        enabled = [row for row in self._rows if row.isEnabled()]
        if enabled:
            row = enabled[index % len(enabled)]
            row.setFocus()
            self._scroll.ensureWidgetVisible(row)

    def eventFilter(self, watched, event):
        kind = event.type()
        if (kind in (QEvent.Type.Close, QEvent.Type.NonClientAreaMouseButtonPress)
                and watched in (self.window(), self.window().windowHandle())):
            # Never consume title-bar input, even if an outside-click release
            # was lost when focus moved to the native window decorations.
            self.close_menu(restore_focus=False)
            return False
        if kind == QEvent.Type.MouseButtonRelease and self._eat_release:
            self._eat_release = False
            return True
        if (kind == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_F10
                and isinstance(watched, QWidget) and watched.window() == self.window()):
            self._toggle(0)
            return True
        if self._current is None:
            return super().eventFilter(watched, event)
        if kind in (QEvent.Type.Enter, QEvent.Type.MouseMove) and watched in self._headings:
            index = self._headings.index(watched)
            if index != self._current:
                self.open_menu(index)
        elif kind == QEvent.Type.MouseButtonPress:
            point = event.globalPosition().toPoint()
            in_panel = self._panel.rect().contains(self._panel.mapFromGlobal(point))
            in_bar = self.rect().contains(self.mapFromGlobal(point))
            if not in_panel and not in_bar:
                self.close_menu()
                # Dismissal must not also draw an atom in the canvas underneath.
                self._eat_release = (isinstance(watched, QWidget)
                                     and watched.window() == self.window())
                return self._eat_release
        elif (kind in (QEvent.Type.Hide, QEvent.Type.Move, QEvent.Type.Resize,
                       QEvent.Type.WindowDeactivate)
              and watched in (self, self.parentWidget(), self.window())):
            self.close_menu(restore_focus=False)
        elif kind == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.close_menu()
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                focused = QApplication.focusWidget()
                if focused in self._rows and focused.isEnabled():
                    focused.click()
                return True
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                step = 1 if key == Qt.Key.Key_Right else -1
                self.open_menu((self._current + step) % len(self._menus))
                return True
            if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Home, Qt.Key.Key_End):
                enabled = [row for row in self._rows if row.isEnabled()]
                current = QApplication.focusWidget()
                index = enabled.index(current) if current in enabled else -1
                target = {Qt.Key.Key_Up: index - 1, Qt.Key.Key_Down: index + 1,
                          Qt.Key.Key_Home: 0, Qt.Key.Key_End: -1}[key]
                self._focus_row(target)
                return True
        return super().eventFilter(watched, event)
