from yugioh_database_linkarrows import LinkArrowSelector
from yugioh_database_displayview1 import DisplayView1
from yugioh_database_global_imports import *

# ===========================
# INITIALIZATION
# ===========================
os.makedirs(JSON_FOLDER, exist_ok=True)
os.makedirs(IMG_FULL_FOLDER, exist_ok=True)
os.makedirs(IMG_CROP_FOLDER, exist_ok=True)

# Remove the ERR.txt file (to remove previous ERRORS and leave only the ones related to this use cycle)
try:
    if os.path.isfile("ERR.txt"):
        os.remove("ERR.txt")
except Exception as e:
    print(e)

# ================================
# MAIN WINDOW APP
# ================================
        
class CardDatabaseApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.cards = []
        self.filtered_cards = []
        self.current_card = None
        self.current_artworks = []
        self.current_art_index = 0

        self.state = [0, 1, 2]
        self.index = 0

        self.search_timer = QTimer()
        self.search_timer.setInterval(160)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.run_filter)

        self.setup_icons()
        self.setup_window()
        self.init_ui()
        self.apply_theme()
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

        # LEFT COLUMN (Fixed width: 1010px)
        self.left_container = QWidget()
        self.left_container.setFixedWidth(1010)
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 1. Dual Filter Panel (Rectangular + Squared, Fixed Height: 185px)
        self.filter_panel = self.create_filter_bar()
        self.filter_panel.setFixedHeight(185)
        left_layout.addWidget(self.filter_panel)

        # 2. Card Display Section (QStackedWidget with Fixed Height: 600px)
        self.statestack = QStackedWidget()
        self.statestack.setFixedHeight(600)

        self.boxstate = DisplayView1()

        # Connect views decoupled via duck-typing signals
        self.boxstate.database_updated.connect(self.on_database_synced)
        self.statestack.addWidget(self.boxstate)

        self.statestack.setCurrentIndex(self.index)
        left_layout.addWidget(self.statestack)

        main_layout.addWidget(self.left_container)

        # RIGHT COLUMN: Results Sidebar (Fixed Width: 350px)
        self.sidebar_widget = self.create_sidebar()
        self.sidebar_widget.setFixedWidth(350)
        main_layout.addWidget(self.sidebar_widget)

    def create_filter_bar(self) -> QWidget:
        filter_container = QWidget()
        h_layout = QHBoxLayout(filter_container)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(10)

        stat_validator = QRegularExpressionValidator(QRegularExpression(r"^-?\d{0,4}$"))

        # Section 1: Rectangular Filters
        self.box_main = QGroupBox("Card Search & Strict Filters")
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
        self.combo_kind.setStyleSheet("""
            QComboBox, QGroupBox QComboBox {
                min-width: 120px;
            }
        """)
        self.combo_kind.currentIndexChanged.connect(self.on_kind_changed)

        lbl_search = QLabel("Search:")
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("Search in Card Name or Effect Text...")
        self.input_search.textChanged.connect(self.trigger_search)

        row0.addWidget(lbl_kind)
        row0.addWidget(self.combo_kind)
        row0.addSpacing(16)
        row0.addWidget(lbl_search)
        row0.addWidget(self.input_search, stretch=1)
        box_layout.addLayout(row0)

        # ROW 1: Classifications
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self.lbl_sub_category = QLabel("Cat:")
        self.combo_sub_category = QComboBox()
        self.combo_sub_category.setIconSize(QSize(18, 18))
        self.combo_sub_category.setStyleSheet("""
            QComboBox, QGroupBox QComboBox {
                min-width: 110px;
            }
        """)
        self.combo_sub_category.addItem("All")
        self.combo_sub_category.currentTextChanged.connect(self.on_sub_category_changed)

        self.lbl_ability = QLabel("Abil:")
        self.combo_ability = QComboBox()
        self.combo_ability.setIconSize(QSize(18, 18))
        self.combo_ability.setStyleSheet("""
            QComboBox, QGroupBox QComboBox {
                min-width: 90px;
            }
        """)
        for ab in MONSTER_ABILITIES:
            self.combo_ability.addItem(ab)
        self.combo_ability.currentTextChanged.connect(self.trigger_search)

        self.lbl_race = QLabel("Type:")
        self.combo_race = QComboBox()
        self.combo_race.setIconSize(QSize(18, 18))
        self.combo_race.setStyleSheet("""
            QComboBox, QGroupBox QComboBox {
                min-width: 120px;
            }
        """)
        for rc in MONSTER_RACES:
            self.combo_race.addItem(rc)
        self.combo_race.currentTextChanged.connect(self.trigger_search)

        self.lbl_attribute = QLabel("Attribute:")
        self.combo_attribute = QComboBox()
        self.combo_attribute.setIconSize(QSize(18, 18))
        self.combo_attribute.setStyleSheet("""
            QComboBox, QGroupBox QComboBox {
                min-width: 110px;
            }
        """)
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

        lbl_def = QLabel("DEF:")
        self.input_def = QLineEdit()
        self.input_def.setPlaceholderText("0 / -1")
        self.input_def.setFixedWidth(64)
        self.input_def.setMaxLength(5)
        self.input_def.setValidator(stat_validator)
        self.input_def.textChanged.connect(self.trigger_search)

        lbl_lvl = QLabel("Level:")
        self.spin_level = QSpinBox()
        self.spin_level.setFixedWidth(82)
        self.spin_level.setRange(-1, 13)
        self.spin_level.setValue(-1)
        self.spin_level.setSpecialValueText("Any")
        self.spin_level.valueChanged.connect(self.trigger_search)

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

        # Section 2: Squared Link Arrow Matrix
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

    # ========================================================================
    # DECOUPLED DATABASE NOTIFICATION LISTENER
    # ========================================================================

    def on_database_synced(self, new_cards: list):
        """Called automatically when any view finishes downloading/updating cards."""
        if new_cards:
            playable_pool = [c for c in new_cards if is_playable_card(c)]
            self.cards = sorted(playable_pool, key=lambda c: c.get("name", "").lower())
            self.run_filter()

    def closeEvent(self, event):
        """Ensures background threads on any stacked view are terminated gracefully."""
        for i in range(self.statestack.count()):
            w = self.statestack.widget(i)
            if hasattr(w, "update_worker") and w.update_worker is not None and w.update_worker.isRunning():
                w.update_worker.requestInterruption()
                w.update_worker.wait(1500)
        super().closeEvent(event)

    # ========================================================================
    # FILTERING & SELECTION HANDLERS
    # ========================================================================

    def on_kind_changed(self):
        kind = self.combo_kind.currentText()
        self.update_filter_state(kind)
        self.trigger_search()

    def update_filter_state(self, kind: str):
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

        else:  # "All"
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
        self.input_search.clear()
        self.input_atk.clear()
        self.input_def.clear()
        self.link_arrow_selector.reset()
        self.combo_kind.setCurrentIndex(0)
        self.trigger_search()

    def trigger_search(self):
        self.search_timer.start()

    def load_cards_from_disk(self):
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

    def run_filter(self):
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
            if q:
                name_val = c.get("name", "").lower()
                desc_val = c.get("desc", "").lower()
                if q not in name_val and q not in desc_val:
                    continue

            frame_type = c.get("frameType", "").lower()
            card_type = c.get("type", "").lower()
            card_race = c.get("race", "")

            if kind == "Spell":
                if frame_type != "spell" and "spell" not in card_type:
                    continue
                if sub_cat != "All" and card_race != sub_cat:
                    continue

            elif kind == "Trap":
                if frame_type != "trap" and "trap" not in card_type:
                    continue
                if sub_cat != "All" and card_race != sub_cat:
                    continue

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

        matched.sort(key=lambda c: c.get("name", "").lower())
        self.filtered_cards = matched
        self.populate_sidebar()

    def populate_sidebar(self):
        self.list_results.clear()
        total = len(self.filtered_cards)

        DISPLAY_CAP = 400
        visible = self.filtered_cards[:DISPLAY_CAP]

        if total > DISPLAY_CAP:
            self.lbl_counter.setText(f"Matches: {total} (Showing first {DISPLAY_CAP})")
        else:
            self.lbl_counter.setText(f"Matches: {total}")

        for card in visible:
            name = card.get("name", "Unknown")
            item = QListWidgetItem(name)
            artworks = resolve_artwork_paths(card)
            if artworks:
                item.setIcon(QIcon(artworks[0]))

            if self.state[self.index] != 1 or artworks:
                item.setData(Qt.UserRole, card)
                self.list_results.addItem(item)

        #if self.list_results.count() > 0:
            #self.list_results.setCurrentRow(0)
            #self.display_current_card(self.list_results.item(0).data(Qt.UserRole))

    def on_card_clicked(self, item: QListWidgetItem):
        card = item.data(Qt.UserRole)
        if card:
            self.display_current_card(card)

    def display_current_card(self, card: dict):
        """Safely updates whichever view widget is currently active in the stack."""
        self.current_card = card
        current_view = self.statestack.currentWidget()
        if current_view and hasattr(current_view, "display_card"):
            current_view.display_card(card)

    def apply_theme(self):
        self.setStyleSheet(GLOBAL_THEME)


if __name__ == "__main__":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    manager = GlobalCursorManager(SourceFetch.IconType.CURSOR_NORMAL.path, SourceFetch.IconType.CURSOR_PRESSED.path)

    window = CardDatabaseApp()
    window.show()
    sys.exit(app.exec())