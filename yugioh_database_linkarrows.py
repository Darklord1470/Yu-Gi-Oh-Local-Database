from yugioh_database_global_imports import *

class LinkArrowSelector(QWidget):
    """
    Uniform 3x3 square matrix for Link Arrow filtering.
    All 9 cells are identically sized squares to guarantee no distortion or overlap.
    """
    markers_changed = Signal(set)

    DIRECTIONS = [
        (0, 0, "Top-Left",     "TopLeft"),
        (0, 1, "Top",          "TopCenter"),
        (0, 2, "Top-Right",    "TopRight"),
        (1, 0, "Left",         "MiddleLeft"),
        (1, 2, "Right",        "MiddleRight"),
        (2, 0, "Bottom-Left",  "BottomLeft"),
        (2, 1, "Bottom",       "BottomCenter"),
        (2, 2, "Bottom-Right", "BottomRight"),
    ]

    CELL_SIZE = 44
    SPACING = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.buttons: dict[str, QToolButton] = {}
        self.active_icons: dict[str, QIcon] = {}
        self.inactive_icons: dict[str, QIcon] = {}
        self.cache: list[int] = []

        total_size = (self.CELL_SIZE * 3) + (self.SPACING * 2) + 10
        self.setFixedSize(total_size, total_size)

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(self.SPACING)

        for i in range(3):
            grid.setRowMinimumHeight(i, self.CELL_SIZE)
            grid.setColumnMinimumWidth(i, self.CELL_SIZE)
            grid.setRowStretch(i, 0)
            grid.setColumnStretch(i, 0)

        for row, col, api_name, suffix in self.DIRECTIONS:
            active_icon = self._resolve_icon(suffix, active=True)
            inactive_icon = self._resolve_icon(suffix, active=False)

            self.active_icons[api_name] = active_icon
            self.inactive_icons[api_name] = inactive_icon

            btn = QToolButton()
            btn.setCheckable(True)
            btn.setFixedSize(self.CELL_SIZE, self.CELL_SIZE)
            btn.setIconSize(QSize(40, 40))
            btn.setIcon(inactive_icon)
            btn.setToolTip(api_name)
            btn.setCursor(Qt.PointingHandCursor)

            btn.setStyleSheet(f"""
                QToolButton {{
                    min-width: {self.CELL_SIZE}px;
                    max-width: {self.CELL_SIZE}px;
                    min-height: {self.CELL_SIZE}px;
                    max-height: {self.CELL_SIZE}px;
                    background-color: #0f3460;
                    border: 1px solid #2d323f;
                    border-radius: 4px;
                    padding: 0px;
                    margin: 0px;
                }}
                QToolButton:hover {{
                    border-color: #fa6969;
                    background-color: #0f3460;
                }}
                QToolButton:checked {{
                    background-color: #0f3460;
                    border: 1px solid #2d323f;
                }}
                QToolButton:checked:hover {{
                    background-color: #0f3460;
                    border: 1px solid #fa6969;
                }}
                QToolButton:disabled {{
                    background-color: #16213e;
                    border-color: #4a5f8a;
                }}
            """)

            btn.toggled.connect(lambda checked, name=api_name: self._on_button_toggled(name, checked))
            grid.addWidget(btn, row, col)
            self.buttons[api_name] = btn

        self.center_lbl = QPushButton()
        self.center_lbl.setText("LINK")
        self.center_lbl.setCheckable(False)
        self.center_lbl.setEnabled(False)
        self.center_lbl.setFixedSize(self.CELL_SIZE, self.CELL_SIZE)

        self.center_lbl.setStyleSheet(f"""
            QPushButton {{
                min-width: {self.CELL_SIZE}px;
                max-width: {self.CELL_SIZE}px;
                min-height: {self.CELL_SIZE}px;
                max-height: {self.CELL_SIZE}px;
                background-color: #16213e;
                border: 1px solid #2d323f;
                border-radius: 4px;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                border-color: #fa6969;
                background-color: #16213e;
            }}
            QPushButton:checked {{
                background-color: #16213e;
                border: 1px solid #2d323f;
            }}
            QPushButton:checked:hover {{
                background-color: #16213e;
                border: 1px solid #fa6969;
            }}
            QPushButton:disabled {{
                background-color: #16213e;
                border-color: #4a5f8a;
            }}
        """)
        grid.addWidget(self.center_lbl, 1, 1)

    def _resolve_icon(self, suffix: str, active: bool) -> QIcon:
        state_tag = "FULL" if active else "EMPTY"
        candidate_attr = f"LM{suffix}{state_tag}"
        if hasattr(SourceFetch.IconType, candidate_attr):
            entry = getattr(SourceFetch.IconType, candidate_attr)
            return sanitize_icon(getattr(entry, "QIcon", entry), QSize(32, 32))
        return QIcon()

    def _on_button_toggled(self, api_name: str, checked: bool):
        direction_names = [d[2] for d in self.DIRECTIONS]
        if api_name in direction_names:
            self.cache.append(direction_names.index(api_name))
            self.cache = self.cache[-8:]

        btn = self.buttons[api_name]
        btn.setIcon(self.active_icons[api_name] if checked else self.inactive_icons[api_name])
        self.markers_changed.emit(self.get_selected_markers())

    def get_selected_markers(self) -> set[str]:
        return {name for name, btn in self.buttons.items() if btn.isChecked()}

    def reset(self):
        for btn in self.buttons.values():
            btn.blockSignals(True)
            btn.setChecked(False)
            btn.setIcon(self.inactive_icons[btn.toolTip()])
            btn.blockSignals(False)

    def setEnabled(self, enabled: bool):
        for btn in self.buttons.values():
            btn.setEnabled(enabled)
