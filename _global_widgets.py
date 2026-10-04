"""
# ======================================
# CUSTOM WIDGETS
# ======================================

Defines and handles the custom widgets created for the app, most notably the custom titlebar and the filtered and colored
textedits. Also the cursor manager to enable the custom cursor.
"""

from yugioh_database_global_imports_root import *
from _global_enums import SourceFetch


# ============================================
# GLOBAL CURSOR MANAGER
# ============================================

class GlobalCursorManager(QObject):
    def __init__(self, normal_cursor_path, pressed_cursor_path, hold_threshold=150):
        super().__init__()

        self.normal_cursor = QCursor(QPixmap(normal_cursor_path),6,1)
        self.pressed_cursor = QCursor(QPixmap(pressed_cursor_path),7,3)
        self.hold_threshold = hold_threshold  # ms

        self._pressed = False
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._switch_to_pressed)

        QApplication.instance().installEventFilter(self)
        QApplication.setOverrideCursor(self.normal_cursor)


    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._pressed = True
            self._timer.start(self.hold_threshold)

        elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            self._pressed = False
            self._timer.stop()
            QApplication.setOverrideCursor(self.normal_cursor)

        return False

    def _switch_to_pressed(self):
        if self._pressed:  
            QApplication.setOverrideCursor(self.pressed_cursor)


# ============================================
# CUSTOM TITLEBAR 
# ============================================

class CustomTitleBar(QWidget):
    def __init__(self, parent, title, icon="", enable_maximize=False, enable_drag=True):
        super().__init__(parent)
        self.parent = parent
        self.dragging = False
        self.offset = QPoint()
        self.setFixedHeight(40)

        # permissions
        self.can_maximize = enable_maximize
        self.can_drag = enable_drag
        
        self.setObjectName("customTitleBar")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 10, 0)
        layout.setSpacing(0)
        
        # title
        self.title_icon = QLabel(f"{SourceFetch.IconType.LOGO_ICON.as_html(26)}")
        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.title.setObjectName("titleBarLabel")
        layout.addWidget(self.title_icon)
        layout.addWidget(self.title)
        
        layout.addStretch()
        
        # pushbuttons minimize, maximize, close
        self.minimize_btn = QPushButton()
        self.minimize_btn.setIcon(SourceFetch.IconType.Line.QIcon)
        self.minimize_btn.setIconSize(QSize(20,20))
        self.minimize_btn.setToolTip("Minimize")
        self.minimize_btn.setObjectName("titleBarButton")
        self.minimize_btn.clicked.connect(parent.showMinimized)
        
        self.maximize_btn = QPushButton()
        self.maximize_btn.setIcon(SourceFetch.IconType.Square.QIcon)
        self.maximize_btn.setIconSize(QSize(20,20))
        self.maximize_btn.setToolTip("Maximize (not available)" if not self.can_maximize else "Maximize")
        self.maximize_btn.setObjectName("titleBarButton")
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        
        self.close_btn = QPushButton()
        self.close_btn.setIcon(SourceFetch.IconType.CrossX.QIcon)
        self.close_btn.setIconSize(QSize(24,24))
        self.close_btn.setToolTip("Close")
        self.close_btn.setObjectName("titleBarCloseButton")
        self.close_btn.clicked.connect(parent.close)
        
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.maximize_btn)
        layout.addWidget(self.close_btn)

    # painter to create the gradient titlebar
    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QLinearGradient, QColor
        
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#667eea"))
        gradient.setColorAt(1, QColor("#764ba2"))
        painter.fillRect(self.rect(), gradient)
    
    
    def toggle_maximize(self):
        if not self.can_maximize:
            return
        
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()
    
    # window drag
    def mousePressEvent(self, event):
        if not self.can_drag:
            return
        
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        if not self.can_drag:
            return
        
        if self.dragging:
            self.parent.move(event.globalPosition().toPoint() - self.offset)
    
    def mouseReleaseEvent(self, event):
        if not self.can_drag:
            return
        
        self.dragging = False
    
    def mouseDoubleClickEvent(self, event):
        self.toggle_maximize()

# =============================================
# SLOW TEXT LOADING LABEL
# =============================================

class TypingLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.full_text = ""
        self.current_index = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._type_next_char)
    
    def type_text(self, text: str, speed_ms: int = 50):

        if speed_ms == 0: # standard Qtextedit/Label behaviour
            self.setText(text)

        else:
            self.full_text = text
            self.current_index = 0
            self.setText("")
            self.timer.start(speed_ms)
        
    def _type_next_char(self):
        if self.current_index < len(self.full_text):
            self.setText(self.full_text[:self.current_index + 1])
            self.current_index += 1
        else:
            self.timer.stop()


# =============================================
# SLOW TEXT (when displayed) TEXTEDIT
# =============================================

class TypingTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.full_text = ""
        self.current_index = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._type_next_char)
    
    def type_text(self, text: str, speed_ms: int = 50):

        if speed_ms == 0: # standard Qtextedit/Label behaviour
            self.setText(text)

        else:
            self.full_text = text
            self.current_index = 0
            self.setText("")
            self.timer.start(speed_ms)
        
    def _type_next_char(self):
        if self.current_index < len(self.full_text):
            self.setText(self.full_text[:self.current_index + 1])
            self.current_index += 1
        else:
            self.timer.stop()
