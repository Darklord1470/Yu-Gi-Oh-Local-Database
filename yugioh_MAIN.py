from yugioh_database_linkarrows import LinkArrowSelector
from yugioh_database_displayview1 import DisplayView1
from yugioh_database_global_imports import *

# =============================================================================
# INITIALIZATION & CLI ARGS
# =============================================================================

# Parse CLI arguments to allow rapid debugging without disk loading
parser = argparse.ArgumentParser(description="Yu-Gi-Oh! Local Database")
parser.add_argument(
    "-prototype",
    action="store_true",
    help="Launch UI in debug mode without loading cards from disk."
)

args, remaining_argv = parser.parse_known_args()

# Guarantee existence of local cache folders (Data, Images, Crops, Thumbnails)
os.makedirs(JSON_FOLDER, exist_ok=True)
os.makedirs(IMG_FULL_FOLDER, exist_ok=True)
os.makedirs(IMG_CROP_FOLDER, exist_ok=True)
os.makedirs(IMG_THUMB_FOLDER, exist_ok=True)

# Clear error log from previous sessions to track only active runtime errors
try:
    if os.path.isfile("ERR.txt"):
        os.remove("ERR.txt")
except Exception as e:
    print(e)

# =============================================================================
# ASYNCHRONOUS CARD LOADER WORKER
# =============================================================================

class CardLoaderWorker(QThread):
    """
    Background worker that iterates through the JSON catalog and parses card data
    without blocking the GUI event loop. Supports cooperative interruption.
    """
    progress_changed = Signal(int, int)  # (current, total)
    loading_finished = Signal(list)      # Loaded and sorted card list

    def __init__(self, json_folder: str = JSON_FOLDER, parent=None):
        super().__init__(parent)
        self.json_folder = json_folder

    def run(self):
        if not os.path.exists(self.json_folder):
            self.loading_finished.emit([])
            return

        # ATTEMPT TO LOAD DATA FROM CACHE
        cache_path = os.path.join(self.json_folder, "_catalog_cache.json")
            
        # Fast path: load the single unified cache file in one read
        if os.path.isfile(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cards_pool = json.load(f)

                cards = [c for c in cards_pool if isinstance(c, dict) and is_playable_card(c)]
                total = len(cards)

                # Update progress bar from 0 to 100%
                self.progress_changed.emit(total, total)

                # Pre-sort alphabetically
                cards.sort(key=lambda c: c.get("name", "").lower())
                self.loading_finished.emit(cards)

                return
            
            except Exception:
                pass

        # NORMAL LOAD IF CACHE LOAD FAILS OR NO CACHE IS FOUND
        json_files = [f for f in os.listdir(self.json_folder) if f.endswith(".json")]
        total = len(json_files)

        if total == 0:
            self.loading_finished.emit([])
            return

        cards = []
        for idx, filename in enumerate(json_files, start=1):
            # Check for cancellation before processing the next file
            if self.isInterruptionRequested():
                return

            file_path = os.path.join(self.json_folder, filename)
            try:
                with open(file_path, "rb") as f:
                    card_data = orjson.loads(f.read())
                    # Filter out non-playable entities (Tokens, Skill cards, Counters)
                    if is_playable_card(card_data):
                        cards.append(card_data)
            except Exception:
                continue

            # Yield GIL and emit progress every 50 files to maintain UI responsiveness
            if idx % 100 == 0 or idx == total:
                self.progress_changed.emit(idx, total)

        if not self.isInterruptionRequested():
            # Pre-sort master list alphabetically by card name for consistent search slicing
            cards.sort(key=lambda c: c.get("name", "").lower())
            self.loading_finished.emit(cards)


# =============================================================================
# START-UP SPLASH WINDOW
# =============================================================================

class DatabaseStartupWindow(QWidget):
    """
    Start-up window displaying database loading progress with an abort button.
    Frameless, translucent, and styled according to the global dark palette.
    """
    database_loaded = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._started = False

        self.setFixedSize(480, 185)
        # Frameless window without WindowStaysOnTopHint (allows switching tasks)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setup_ui()
        self.center_on_screen()

        # Connect background card reader thread
        self.worker = CardLoaderWorker()
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.loading_finished.connect(self.on_finished)

    def setup_ui(self):
        container = QFrame(self)
        container.setObjectName("startupFrame")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 20, 24, 20)
        container_layout.setSpacing(10)

        # 1. Main Title
        self.lbl_title = QLabel("Loading Database")
        self.lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("color: #667eea;")

        # 2. Loading Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #0f3460;
                border: 1px solid #4a5f8a;
                border-radius: 6px;
                color: #eee;
                font-weight: bold;
                font-size: 9pt;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #667eea, stop:1 #764ba2);
                border-radius: 5px;
            }
        """)

        container_layout.addWidget(self.lbl_title)
        container_layout.addWidget(self.progress_bar)

        # 3. Bottom Row: Card Counter / Status + Stop Button
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 4, 0, 0)
        bottom_row.setSpacing(10)

        self.lbl_status = QLabel("Scanning card catalog...")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #ffffff;")
        bottom_row.addWidget(self.lbl_status, stretch=1)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.abort_loading)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #667eea, stop:1 #764ba2);
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #7b93ff, stop:1 #8b5bc7);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #5568d3, stop:1 #633a87);
                padding-top: 12px;
                padding-bottom: 8px;
            }
            QPushButton:disabled {
                background: rgba(42, 42, 62, 0.6);
                color: #666;
            }
        """)
        bottom_row.addWidget(self.btn_stop)

        container_layout.addLayout(bottom_row)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(container)

        self.setStyleSheet("""
            #startupFrame {
                background-color: #16213e;
                border: 2px solid #4a5f8a;
                border-radius: 10px;
            }
        """)

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2
            )

    def showEvent(self, event):
        super().showEvent(event)
        if not self._started:
            self._started = True
            self.worker.start()

    def on_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.lbl_status.setText(f"Loading cards: {current:,} / {total:,}")

    def on_finished(self, loaded_cards: list):
        self.database_loaded.emit(loaded_cards)

    def abort_loading(self):
        """Cooperatively stops the loader thread and exits the application immediately."""
        if self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(1000)
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(1000)
        super().closeEvent(event)


# =============================================================================
# MAIN WINDOW APP
# =============================================================================

class CardDatabaseApp(QMainWindow):
    def __init__(self, debug_mode: bool = False, initial_cards: list = None):
        super().__init__()

        self.cards = initial_cards if initial_cards is not None else []
        self.filtered_cards = []
        self.current_card = None
        self.current_artworks = []
        self.current_art_index = 0

        # View states: 0 = DisplayView1, 1 = DisplayView2 (Crop/Editor), 2 = DisplayView3
        self.state = [0, 1, 2]
        self.index = 0

        # Search debounce timer: resets on keystroke to avoid executing redundant queries
        self.search_timer = QTimer()
        self.search_timer.setInterval(500)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.run_filter)

        self.setup_icons()
        self.setup_window()
        self.init_ui()
        self.apply_theme()

        if not debug_mode:
            if initial_cards is not None:
                self.run_filter()
            else:
                self.load_cards_from_disk()

    def setup_icons(self):
        """Constructs sanitized icon caches safely AFTER QApplication is alive."""
        self.card_kinds_icons = [
            QIcon(),
            sanitize_icon(SourceFetch.IconType.Monster.QIcon),
            sanitize_icon(SourceFetch.IconType.Spell.QIcon),
            sanitize_icon(SourceFetch.IconType.Trap.QIcon)
        ]
        self.spell_icons = [
            QIcon(),
            sanitize_icon(SourceFetch.IconType.SpellNormal.QIcon),
            sanitize_icon(SourceFetch.IconType.SpellQuickPlay.QIcon),
            sanitize_icon(SourceFetch.IconType.SpellContinuous.QIcon),
            sanitize_icon(SourceFetch.IconType.SpellEquip.QIcon),
            sanitize_icon(SourceFetch.IconType.SpellField.QIcon),
            sanitize_icon(SourceFetch.IconType.SpellRitual.QIcon)
        ]
        self.trap_icons = [
            QIcon(),
            sanitize_icon(SourceFetch.IconType.TrapNormal.QIcon),
            sanitize_icon(SourceFetch.IconType.TrapContinuous.QIcon),
            sanitize_icon(SourceFetch.IconType.TrapCounter.QIcon)
        ]
        self.attribute_icons = [
            QIcon(),
            sanitize_icon(SourceFetch.IconType.Fire.QIcon),
            sanitize_icon(SourceFetch.IconType.Water.QIcon),
            sanitize_icon(SourceFetch.IconType.Wind.QIcon),
            sanitize_icon(SourceFetch.IconType.Earth.QIcon),
            sanitize_icon(SourceFetch.IconType.Light.QIcon),
            sanitize_icon(SourceFetch.IconType.Dark.QIcon),
            sanitize_icon(SourceFetch.IconType.Divine.QIcon)
        ]

    def setup_window(self):
        self.setWindowTitle("Yu-Gi-Oh! Local Card Database")
        self.setFixedSize(1400, 860)
        self.setWindowIcon(SourceFetch.IconType.LOGO_ICON.QIcon)
        self.setWindowFlags(Qt.FramelessWindowHint)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.top_layout = QVBoxLayout(central_widget)
        self.top_layout.setSpacing(0)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_bar = CustomTitleBar(self, "Yu-Gi-Oh! Local Card Database", enable_maximize=False, enable_drag=True)
        self.top_layout.addWidget(self.title_bar)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)
        self.top_layout.addLayout(main_layout)

        # LEFT COLUMN: Controls, Filters & Main Card View Stack (Fixed width: 1010px)
        self.left_container = QWidget()
        self.left_container.setFixedWidth(1010)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 1. Dual Filter Panel (Search bar + categorical + numeric filters + link matrix)
        self.filter_panel = self.create_filter_bar()
        self.filter_panel.setFixedHeight(185)
        left_layout.addWidget(self.filter_panel)

        # 2. Card Display Section (QStackedWidget with Fixed Height: 600px)
        self.statestack = QStackedWidget()
        self.statestack.setFixedHeight(600)

        self.boxstate1 = DisplayView1()

        # Connect decoupled update signals so card pool re-indexes on sync
        self.boxstate1.database_updated.connect(self.on_database_synced)
        self.statestack.addWidget(self.boxstate1)

        self.statestack.setCurrentIndex(self.index)
        left_layout.addWidget(self.statestack)

        main_layout.addWidget(self.left_container)

        # RIGHT COLUMN: Results Sidebar with fast thumbnail list (Fixed Width: 350px)
        self.sidebar_widget = self.create_sidebar()
        self.sidebar_widget.setFixedWidth(350)
        main_layout.addWidget(self.sidebar_widget)

    def create_filter_bar(self) -> QWidget:
        filter_container = QWidget()
        h_layout = QHBoxLayout(filter_container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)

        stat_validator = QRegularExpressionValidator(QRegularExpression(r"^-?\d{0,4}$"))

        # Section 1: Rectangular Filters (Text, Dropdowns, Numeric)
        self.box_main = QGroupBox("Card Search Filters")
        box_layout = QVBoxLayout(self.box_main)
        box_layout.setContentsMargins(14, 8, 14, 8)
        box_layout.setSpacing(8)

        # ROW 0: Kind & Search
        row0 = QHBoxLayout()
        row0.setSpacing(6)

        lbl_kind = QLabel("Kind:")
        self.combo_kind = QComboBox()
        self.combo_kind.setIconSize(QSize(18, 18))
        for icon, text in zip(self.card_kinds_icons, CARD_KINDS):
            if icon and not icon.isNull():
                self.combo_kind.addItem(icon, text)
            else:
                self.combo_kind.addItem(text)
        self.combo_kind.setStyleSheet("QComboBox, QGroupBox QComboBox { min-width: 120px; }")
        self.combo_kind.currentIndexChanged.connect(self.on_kind_changed)
        self.combo_kind.setToolTip("KIND: the main kind of Yu-Gi-OH cards (Monster/Spell/Trap)")
        self.combo_kind.setToolTipDuration(5000)

        lbl_search = QLabel("Search:")
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Search in Card Name or Effect Text...")
        self.input_search.setToolTip(
            "SEARCH: search cards whose name or card text contains the input string.\n\n" \
            "Can be used in 2 main ways:\n" \
            "● search 'archetypes' (es. Dragunity/Sky Striker/Memento)\n" \
            "● search 'interactions' (es. discard/draw/banish/target)"
        )
        self.input_search.setToolTipDuration(5000)

        # Execute text search only when the user is not actively typing trailing whitespace
        self.input_search.textChanged.connect(
            lambda: self.trigger_search() if (len(self.input_search.text()) > 0 and self.input_search.text()[-1] != " ") else None
        )

        row0.addWidget(lbl_kind)
        row0.addWidget(self.combo_kind)
        row0.addSpacing(16)
        row0.addWidget(lbl_search)
        row0.addWidget(self.input_search, stretch=1)
        box_layout.addLayout(row0)

        # ROW 1: Classifications (Category, Ability, Race/Type, Attribute)
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self.lbl_sub_category = QLabel("Cat:")
        self.combo_sub_category = QComboBox()
        self.combo_sub_category.setIconSize(QSize(18, 18))
        self.combo_sub_category.setStyleSheet("QComboBox, QGroupBox QComboBox { min-width: 110px; }")
        self.combo_sub_category.addItem("All")
        self.combo_sub_category.currentTextChanged.connect(self.on_sub_category_changed)
        self.combo_sub_category.setToolTip(
            "CATEGORY: subcategories of the main kinds of cards.\n\n" \
            "For Monsters: Normal, Effect, Ritual, Fusion, Synchro, Xyz, Pendulum, Link.\n" \
            "For Spells: Normal, Continuous, Equip, Quick-Play, Ritual, Field.\n" \
            "For Traps: Normal, Continuous, Counter."
        )
        self.combo_sub_category.setToolTipDuration(5000)

        self.lbl_ability = QLabel("Abil:")
        self.combo_ability = QComboBox()
        self.combo_ability.setIconSize(QSize(18, 18))
        self.combo_ability.setStyleSheet("QComboBox, QGroupBox QComboBox { min-width: 90px; }")
        self.combo_ability.setToolTip("SPECIAL TYPES: additional types of Monster Cards (es. Tuner, Gemini, Union).")
        self.combo_ability.setToolTipDuration(5000)
        for ab in MONSTER_ABILITIES:
            self.combo_ability.addItem(ab)
        self.combo_ability.currentTextChanged.connect(self.trigger_search)

        self.lbl_race = QLabel("Type:")
        self.combo_race = QComboBox()
        self.combo_race.setIconSize(QSize(18, 18))
        self.combo_race.setStyleSheet("QComboBox, QGroupBox QComboBox { min-width: 120px; }")
        self.combo_race.setToolTip("TYPES: types of Monster Cards (es. Spellcaster, Warrior, Illusion).")
        self.combo_race.setToolTipDuration(5000)
        for rc in MONSTER_RACES:
            self.combo_race.addItem(rc)
        self.combo_race.currentTextChanged.connect(self.trigger_search)

        self.lbl_attribute = QLabel("Attribute:")
        self.combo_attribute = QComboBox()
        self.combo_attribute.setIconSize(QSize(18, 18))
        self.combo_attribute.setStyleSheet("QComboBox, QGroupBox QComboBox { min-width: 110px; }")
        self.combo_attribute.setToolTip("ATTRIBUTE: attribute of Monster Cards (LIGHT, DARK, WIND, EARTH, FIRE, WATER, DIVINE).")
        self.combo_attribute.setToolTipDuration(5000)
        for icon, att in zip(self.attribute_icons, ATTRIBUTES):
            if icon and not icon.isNull():
                self.combo_attribute.addItem(icon, att)
            else:
                self.combo_attribute.addItem(att)
        self.combo_attribute.currentTextChanged.connect(self.trigger_search)

        row1.addWidget(self.lbl_sub_category)
        row1.addWidget(self.combo_sub_category)
        row1.addSpacing(8)
        row1.addWidget(self.lbl_ability)
        row1.addWidget(self.combo_ability)
        row1.addSpacing(8)
        row1.addWidget(self.lbl_race)
        row1.addWidget(self.combo_race)
        row1.addSpacing(8)
        row1.addWidget(self.lbl_attribute)
        row1.addWidget(self.combo_attribute)
        row1.addStretch()
        box_layout.addLayout(row1)

        # ROW 2: Numeric ATK/DEF, Scales, Link Rating & Reset Button
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        lbl_atk = QLabel("ATK:")
        self.input_atk = QLineEdit()
        self.input_atk.setPlaceholderText("0 / -1")
        self.input_atk.setFixedWidth(64)
        self.input_atk.setMaxLength(5)
        self.input_atk.setValidator(stat_validator)
        self.input_atk.textChanged.connect(self.trigger_search)
        self.input_atk.setToolTip(
            "ATK: use to search Monster Cards with a specific attack value.\n\n" \
            "NOTE: to search Monster Cards with '?' atk, input '-1'."
        )
        self.input_atk.setToolTipDuration(5000)

        lbl_def = QLabel("DEF:")
        self.input_def = QLineEdit()
        self.input_def.setPlaceholderText("0 / -1")
        self.input_def.setFixedWidth(64)
        self.input_def.setMaxLength(5)
        self.input_def.setValidator(stat_validator)
        self.input_def.textChanged.connect(self.trigger_search)
        self.input_def.setToolTip(
            "DEF: use to search Monster Cards with a specific defense value.\n\n" \
            "NOTE: to search Monster Cards with '?' def, input '-1'."
        )
        self.input_def.setToolTipDuration(5000)

        lbl_lvl = QLabel("Level:")
        self.spin_level = QSpinBox()
        self.spin_level.setFixedWidth(82)
        self.spin_level.setRange(-1, 13)
        self.spin_level.setValue(-1)
        self.spin_level.setSpecialValueText("Any")
        self.spin_level.valueChanged.connect(self.trigger_search)
        self.spin_level.setToolTip(
            "LEVEL: use to search Monster Cards with a specific level/rank value.\n\n" \
            "NOTE: to search Monster Cards without level/rank, select '0'."
        )
        self.spin_level.setToolTipDuration(5000)

        lbl_scale = QLabel("Scale:")
        self.spin_scale = QSpinBox()
        self.spin_scale.setFixedWidth(82)
        self.spin_scale.setRange(-1, 13)
        self.spin_scale.setValue(-1)
        self.spin_scale.setSpecialValueText("Any")
        self.spin_scale.valueChanged.connect(self.trigger_search)

        lbl_link = QLabel("Link:")
        self.spin_link = QSpinBox()
        self.spin_link.setFixedWidth(82)
        self.spin_link.setRange(-1, 6)
        self.spin_link.setValue(-1)
        self.spin_link.setSpecialValueText("Any")
        self.spin_link.valueChanged.connect(self.trigger_search)

        btn_reset = QPushButton("Reset")
        btn_reset.setFixedWidth(100)
        btn_reset.clicked.connect(self.reset_filters)

        row2.addWidget(lbl_atk)
        row2.addWidget(self.input_atk)
        row2.addSpacing(6)
        row2.addWidget(lbl_def)
        row2.addWidget(self.input_def)
        row2.addSpacing(6)
        row2.addWidget(lbl_lvl)
        row2.addWidget(self.spin_level)
        row2.addSpacing(6)
        row2.addWidget(lbl_scale)
        row2.addWidget(self.spin_scale)
        row2.addSpacing(6)
        row2.addWidget(lbl_link)
        row2.addWidget(self.spin_link)
        row2.addStretch()
        row2.addWidget(btn_reset)
        box_layout.addLayout(row2)

        h_layout.addWidget(self.box_main, stretch=1)

        # Section 2: Squared Link Arrow Matrix (Fixed 185x185 box)
        self.box_arrows = QGroupBox("Link Arrows")
        self.box_arrows.setFixedSize(185, 185)
        arrows_layout = QVBoxLayout(self.box_arrows)
        arrows_layout.setContentsMargins(0, 0, 0, 0)
        arrows_layout.setSpacing(0)
        arrows_layout.setAlignment(Qt.AlignCenter)

        self.link_arrow_selector = LinkArrowSelector()
        self.link_arrow_selector.markers_changed.connect(self.trigger_search)
        arrows_layout.addWidget(self.link_arrow_selector)

        h_layout.addWidget(self.box_arrows)

        self.update_filter_state("All")
        return filter_container

    def create_sidebar(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.lbl_counter = QLabel("Results: 0")
        self.lbl_counter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.lbl_counter)

        self.list_results = QListWidget()
        self.list_results.setIconSize(QSize(38, 55))
        self.list_results.setUniformItemSizes(True)
        self.list_results.itemClicked.connect(self.on_card_clicked)
        layout.addWidget(self.list_results)

        return container

    def on_database_synced(self, new_cards: list):
        """Automatically updates the in-memory pool when a background update completes."""
        if new_cards:
            playable_pool = [c for c in new_cards if is_playable_card(c)]
            self.cards = sorted(playable_pool, key=lambda c: c.get("name", "").lower())
            self.run_filter()

    def closeEvent(self, event):
        """Gracefully aborts any active update threads before window destruction."""
        for i in range(self.statestack.count()):
            w = self.statestack.widget(i)
            if hasattr(w, "update_worker") and w.update_worker is not None and w.update_worker.isRunning():
                w.update_worker.requestInterruption()
                w.update_worker.wait(1500)
        super().closeEvent(event)

    def on_kind_changed(self):
        kind = self.combo_kind.currentText()
        self.update_filter_state(kind)
        self.trigger_search()

    def on_advance_state(self):
        """Cycles through DisplayView1 -> DisplayView2 -> DisplayView3."""
        self.index = (self.index + 1) % len(self.state)
        self.statestack.setCurrentIndex(self.index)
        self.trigger_search()

    def update_filter_state(self, kind: str):
        """Enables/disables monster-specific inputs depending on whether Kind is Monster, Spell, or Trap."""
        self.combo_sub_category.blockSignals(True)
        self.combo_sub_category.clear()

        if kind == "Monster":
            self.combo_sub_category.setEnabled(True)
            for cat in MONSTER_CATEGORIES:
                self.combo_sub_category.addItem(cat)

            self.combo_ability.setEnabled(True)
            self.combo_race.setEnabled(True)
            self.combo_attribute.setEnabled(True)
            self.input_atk.setEnabled(True)
            self.input_def.setEnabled(True)
            self.spin_level.setEnabled(True)
            self.spin_scale.setEnabled(True)
            self.spin_link.setEnabled(True)

            self.box_arrows.setEnabled(True)
            self.link_arrow_selector.setEnabled(True)

        elif kind == "Spell":
            self.combo_sub_category.setEnabled(True)
            for icon, prop in zip(self.spell_icons, SPELL_PROPERTIES):
                if icon and not icon.isNull():
                    self.combo_sub_category.addItem(icon, prop)
                else:
                    self.combo_sub_category.addItem(prop)
            self.disable_monster_filters()

        elif kind == "Trap":
            self.combo_sub_category.setEnabled(True)
            for icon, prop in zip(self.trap_icons, TRAP_PROPERTIES):
                if icon and not icon.isNull():
                    self.combo_sub_category.addItem(icon, prop)
                else:
                    self.combo_sub_category.addItem(prop)
            self.disable_monster_filters()

        else:
            self.combo_sub_category.addItem("All")
            self.combo_sub_category.setEnabled(False)
            self.disable_monster_filters()

        self.combo_sub_category.blockSignals(False)

    def disable_monster_filters(self):
        for widget in [self.combo_ability, self.combo_race, self.combo_attribute]:
            widget.blockSignals(True)
            widget.setCurrentIndex(0)
            widget.setEnabled(False)
            widget.blockSignals(False)

        for inp in [self.input_atk, self.input_def]:
            inp.blockSignals(True)
            inp.clear()
            inp.setEnabled(False)
            inp.blockSignals(False)

        for spin in [self.spin_level, self.spin_scale, self.spin_link]:
            spin.blockSignals(True)
            spin.setValue(-1)
            spin.setEnabled(False)
            spin.blockSignals(False)

        self.link_arrow_selector.reset()
        self.link_arrow_selector.setEnabled(False)

    def on_sub_category_changed(self):
        sub_cat = self.combo_sub_category.currentText()
        if self.combo_kind.currentText() == "Monster":
            is_link = (sub_cat == "Link")
            self.input_def.setEnabled(not is_link)
            self.spin_level.setEnabled(not is_link)
            if is_link:
                self.input_def.clear()
                self.spin_level.setValue(-1)
        self.trigger_search()

    def reset_filters(self):
        """Clears all inputs and resets filter states to default."""
        self.input_search.clear()
        self.input_atk.clear()
        self.input_def.clear()
        self.link_arrow_selector.reset()
        self.combo_kind.setCurrentIndex(0)
        self.trigger_search()

    def trigger_search(self):
        """Debounces search execution using the single-shot countdown timer."""
        self.search_timer.start()

    def load_cards_from_disk(self):
        """Synchronously loads all card JSONs from disk (used only when launched without splash)."""
        if not os.path.exists(JSON_FOLDER):
            self.lbl_counter.setText("Folder 'cards_data' missing!")
            return

        json_files = [f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")]
        self.cards.clear()

        for filename in json_files:
            file_path = os.path.join(JSON_FOLDER, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    card_data = json.load(f)
                    if is_playable_card(card_data):
                        self.cards.append(card_data)
            except Exception:
                continue

        self.cards.sort(key=lambda c: c.get("name", "").lower())
        self.run_filter()

    def run_filter(self, max_matches: int = 40000):
        """
        Executes strict filtering over the card pool.
        Terminates iteration early once `max_matches` is reached to prevent UI lag.
        """
        q = self.input_search.text().strip().lower()
        kind = self.combo_kind.currentText()
        sub_cat = self.combo_sub_category.currentText()
        ability = self.combo_ability.currentText()
        race = self.combo_race.currentText()
        attr = self.combo_attribute.currentText()

        def parse_stat(txt: str):
            try:
                return int(txt)
            except ValueError:
                return None

        atk_val = parse_stat(self.input_atk.text().strip())
        def_val = parse_stat(self.input_def.text().strip())

        lvl = self.spin_level.value()
        scale = self.spin_scale.value()
        link = self.spin_link.value()
        selected_markers = self.link_arrow_selector.get_selected_markers()

        matched = []
        for c in self.cards:
            # Name and Description filter
            if q:
                name_val = c.get("name", "").lower()
                desc_val = c.get("desc", "").lower()
                if q not in name_val and q not in desc_val:
                    continue

            frame_type = c.get("frameType", "").lower()
            card_type = c.get("type", "").lower()
            card_race = c.get("race", "")

            # 1. Spell filter
            if kind == "Spell":
                if frame_type != "spell" and "spell" not in card_type:
                    continue
                if sub_cat != "All" and card_race != sub_cat:
                    continue

            # 2. Trap filter
            elif kind == "Trap":
                if frame_type != "trap" and "trap" not in card_type:
                    continue
                if sub_cat != "All" and card_race != sub_cat:
                    continue

            # 3. Monster filter
            elif kind == "Monster":
                if frame_type in ["spell", "trap"] or "spell" in card_type or "trap" in card_type:
                    continue

                if sub_cat != "All":
                    sc = sub_cat.lower()
                    if sc == "normal" and ("normal" not in frame_type or "pendulum" in frame_type):
                        continue
                    elif sc == "effect" and ("effect" not in frame_type or "pendulum" in frame_type):
                        continue
                    elif sc == "pendulum" and "pendulum" not in frame_type:
                        continue
                    elif sc in ["ritual", "fusion", "synchro", "xyz", "link"] and sc not in frame_type:
                        continue

                if ability != "All" and ability.lower() not in card_type:
                    continue
                if race != "All" and card_race != race:
                    continue
                if attr != "All" and c.get("attribute") != attr:
                    continue

                if atk_val is not None and c.get("atk") != atk_val:
                    continue
                if def_val is not None and c.get("def") != def_val:
                    continue

                if lvl != -1 and c.get("level") != lvl:
                    continue
                if scale != -1 and c.get("scale") != scale:
                    continue
                if link != -1 and c.get("linkval") != link:
                    continue

                if selected_markers:
                    card_markers = set(c.get("linkmarkers") or [])
                    if not selected_markers.issubset(card_markers):
                        continue

            matched.append(c)

            # Early termination cut-off
            if len(matched) >= max_matches:
                break

        matched.sort(key=lambda c: c.get("name", "").lower())
        self.filtered_cards = matched
        self.populate_sidebar()

    def populate_sidebar(self):
        """
        Populates the search results sidebar list with card names and icons.
        Utilizes pre-baked 38x55 thumbnails from IMG_THUMB_FOLDER to achieve near-instantaneous
        UI rendering without reading or downscaling heavy full-resolution artworks on the main thread.
        """
        self.list_results.clear()
        total = len(self.filtered_cards)

        DISPLAY_CAP = 400
        visible = self.filtered_cards[:DISPLAY_CAP]

        if total > DISPLAY_CAP:
            self.lbl_counter.setText(f"Matches: {total} (Showing first {DISPLAY_CAP})")
        else:
            self.lbl_counter.setText(f"Matches: {total}")

        is_crop_view = (self.state[self.index] == 1)

        for card in visible:
            name = card.get("name", "Unknown")
            item = QListWidgetItem(name)

            artworks = None
            # In Crop View (State 1), verify that crop artworks actually exist for this card
            if is_crop_view:
                artworks = resolve_artwork_paths(card, True)
                if not artworks:
                    # Skip cards without cropped artwork in State 1
                    continue

            # Construct primary thumbnail path: {card_id}_{primary_art_id}.png
            card_id = str(card.get("id", ""))
            card_images = card.get("card_images", [])
            primary_art_id = str(card_images[0].get("id", card_id)) if card_images else card_id
            thumb_path = os.path.join(IMG_THUMB_FOLDER, f"{card_id}_{primary_art_id}.png")

            # 1. Attempt to load the pre-baked 38x55 thumbnail (fast 2KB read, no resizing overhead)
            if os.path.isfile(thumb_path):
                item.setIcon(QIcon(thumb_path))
            else:
                # 2. Fallback: resolve high-resolution image path if thumbnail is not yet baked
                if artworks is None:
                    artworks = resolve_artwork_paths(card, is_crop_view)
                if artworks:
                    item.setIcon(QIcon(artworks[0]))

            # Register card metadata in the item payload and attach to sidebar list
            item.setData(Qt.UserRole, card)
            self.list_results.addItem(item)

        if self.list_results.count() > 0:
            self.list_results.setCurrentRow(0)

    def on_card_clicked(self, item: QListWidgetItem):
        card = item.data(Qt.UserRole)
        if card:
            self.display_current_card(card)

    def display_current_card(self, card: dict):
        """Passes the active card dictionary to whichever View widget is currently visible."""
        self.current_card = card
        current_view = self.statestack.currentWidget()
        if current_view and hasattr(current_view, "display_card"):
            current_view.display_card(card)

    def apply_theme(self):
        self.setStyleSheet(GLOBAL_THEME)


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication([sys.argv[0]] + remaining_argv)
    manager = GlobalCursorManager(SourceFetch.IconType.CURSOR_NORMAL.path, SourceFetch.IconType.CURSOR_PRESSED.path)

    # 1. Prototype Mode (-prototype flag passed): Skip splash and disk load entirely
    if args.prototype:
        window = CardDatabaseApp(debug_mode=True)
        window.show()
        sys.exit(app.exec())

    # 2. Standard Startup with Animated Progress Window
    splash = DatabaseStartupWindow()
    main_window = None

    def launch_main_window(loaded_cards: list):
        nonlocal main_window
        main_window = CardDatabaseApp(debug_mode=False, initial_cards=loaded_cards)
        main_window.show()
        splash.close()

    splash.database_loaded.connect(launch_main_window)
    splash.show()
    splash.raise_()
    splash.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()