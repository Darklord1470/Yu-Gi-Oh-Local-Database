from yugioh_database_global_imports import *
from yugioh_database_update import DatabaseUpdateWorker
from yugioh_database_cardcanvas import CardViewCanvas

class DisplayView1(QFrame):
    """
    Decoupled Card Display View that inherits directly from QFrame to guarantee 100% width fill.
    Manages its own UI state and background DB worker autonomously.
    """
    database_updated = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = 0
        self.current_card = None
        self.current_artworks = []
        self.current_art_index = 0
        self.update_worker = None

        self.setFrameShape(QFrame.StyledPanel)
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(14)

        # Left Column: Image Canvas
        self.card_canvas = CardViewCanvas(size_mult=(1.014, 1.014))
        layout.addWidget(self.card_canvas)

        # Right Column: Metadata, Description & Bottom Bar
        details_col = QVBoxLayout()
        details_col.setContentsMargins(0, 0, 0, 0)
        details_col.setSpacing(6)

        self.lbl_name = QLabel("Select a Card")
        self.lbl_name.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.lbl_name.setWordWrap(True)
        details_col.addWidget(self.lbl_name)

        self.lbl_type_line = QLabel("")
        self.lbl_type_line.setStyleSheet("font-size: 10pt; color: #58a6ff;")
        details_col.addWidget(self.lbl_type_line)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_stats.setStyleSheet("color: #e6edf3;")
        details_col.addWidget(self.lbl_stats)

        details_col.addWidget(QLabel(f"Card Text"))
        self.txt_desc = TypingTextEdit()
        self.txt_desc.setReadOnly(True)
        self.txt_desc.setFont(QFont("Segoe UI", 10))
        details_col.addWidget(self.txt_desc, stretch=1)

        # Card ID & Online Image Link Bar
        self.id_bar = QWidget()
        self.id_bar.setFixedHeight(24)
        id_layout = QHBoxLayout(self.id_bar)
        id_layout.setContentsMargins(0, 2, 0, 2)
        id_layout.setSpacing(12)

        self.lbl_card_id = QLabel("Card ID: -")
        self.lbl_card_id.setStyleSheet("font-weight: bold; font-size: 9pt;")

        self.lbl_image_link = QLabel("")
        self.lbl_image_link.setOpenExternalLinks(True)
        self.lbl_image_link.setStyleSheet("font-size: 9pt;")

        id_layout.addWidget(self.lbl_card_id)
        id_layout.addWidget(self.lbl_image_link)
        id_layout.addStretch()
        details_col.addWidget(self.id_bar)

        # Bottom Button Bar
        self.bottom_bar = QWidget()
        self.bottom_bar.setFixedHeight(36)
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        self.btn_prev_art = QPushButton("◀ Prev")
        self.btn_prev_art.setStyleSheet("""
            QPushButton {
                min-width: 20px;
            }
        """)
        self.btn_prev_art.clicked.connect(self.prev_artwork)

        self.lbl_art_counter = QLabel("Artwork 1 / 1")
        self.lbl_art_counter.setAlignment(Qt.AlignCenter)
        self.lbl_art_counter.setStyleSheet("font-weight: bold;")

        self.btn_next_art = QPushButton("Next ▶")
        self.btn_next_art.setStyleSheet("""
            QPushButton {
                min-width: 20px;
            }
        """)
        self.btn_next_art.clicked.connect(self.next_artwork)

        bottom_layout.addWidget(self.btn_prev_art)
        bottom_layout.addWidget(self.lbl_art_counter)
        bottom_layout.addWidget(self.btn_next_art)

        bottom_layout.addStretch()

        self.btn_quick_refresh_db = QPushButton(" Fast Update")
        self.btn_quick_refresh_db.setIcon(sanitize_icon(SourceFetch.IconType.Download.QIcon))
        self.btn_quick_refresh_db.setObjectName("quickRefreshBtn")
        self.btn_quick_refresh_db.setFixedWidth(150)
        self.btn_quick_refresh_db.clicked.connect(lambda: self.download_card_data("fast"))
        bottom_layout.addWidget(self.btn_quick_refresh_db)

        self.btn_refresh_db = QPushButton(" Full Update")
        self.btn_refresh_db.setIcon(sanitize_icon(SourceFetch.IconType.Download.QIcon))
        self.btn_refresh_db.setObjectName("refreshBtn")
        self.btn_refresh_db.setFixedWidth(150)
        self.btn_refresh_db.clicked.connect(lambda: self.download_card_data("full"))
        bottom_layout.addWidget(self.btn_refresh_db)

        details_col.addWidget(self.bottom_bar)
        layout.addLayout(details_col)

    # ========================================================================
    # AUTONOMOUS DATABASE REFRESH WORKER
    # ========================================================================

    def download_card_data(self, fetch_mode: str):
        if self.update_worker is not None and self.update_worker.isRunning():
            return

        if fetch_mode == "fast":
            self.btn_quick_refresh_db.setEnabled(False)
            self.btn_quick_refresh_db.setText("Syncing...")

        if fetch_mode == "full":
            self.btn_refresh_db.setEnabled(False)
            self.btn_refresh_db.setText("Syncing...")

        self.update_worker = DatabaseUpdateWorker()
        self.update_worker.status_changed.connect(lambda msg: self._on_sync_status(msg, fetch_mode))
        self.update_worker.progress_changed.connect(lambda cur,tot: self._on_sync_progress(cur, tot, fetch_mode))
        self.update_worker.sync_finished.connect(lambda cards, downloaded, errors: self._on_sync_finished(cards, downloaded, errors, fetch_mode))
        self.update_worker.error_occurred.connect(lambda err_msg: self._on_sync_error(err_msg, fetch_mode))

        if fetch_mode == "fast":
            self.update_worker.sync_quick()

        if fetch_mode == "full":
            self.update_worker.sync_full()

    def _on_sync_status(self, message: str, fetch_mode: str):
        display_text = message if len(message) <= 15 else message[:16] + "..."

        if fetch_mode == "fast":
            self.btn_quick_refresh_db.setText(display_text)

        if fetch_mode == "full":
            self.btn_refresh_db.setText(display_text)

    def _on_sync_progress(self, current: int, total: int, fetch_mode: str):
        if fetch_mode == "fast":
            self.btn_quick_refresh_db.setText(f"Img: {current}/{total}")

        if fetch_mode == "full":
            self.btn_refresh_db.setText(f"Img: {current}/{total}")

    def _on_sync_finished(self, new_cards: list, downloaded: int, errors: int, fetch_mode: str):
        if fetch_mode == "fast":
            self.btn_quick_refresh_db.setEnabled(True)
            self.btn_quick_refresh_db.setText(" Fast Update")

        if fetch_mode == "full":
            self.btn_refresh_db.setEnabled(True)
            self.btn_refresh_db.setText(" Full Update")

        # Notify the parent application of the new card pool cleanly via Qt Signal
        self.database_updated.emit(new_cards)

    def _on_sync_error(self, err_msg: str, fetch_mode: str):
        if fetch_mode == "fast":
            self.btn_quick_refresh_db.setEnabled(True)
            self.btn_quick_refresh_db.setText(" Fast Update")

        if fetch_mode == "full":
            self.btn_refresh_db.setEnabled(True)
            self.btn_refresh_db.setText(" Full Update")

        print(f"[Sync Error] {err_msg}")

    def closeEvent(self, event):
        if self.update_worker is not None and self.update_worker.isRunning():
            self.update_worker.requestInterruption()
            self.update_worker.wait(1500)
        super().closeEvent(event)

    # ========================================================================
    # CARD DISPLAY LOGIC
    # ========================================================================

    def display_card(self, card: dict):
        self.current_card = card
        self.lbl_name.setText(card.get("name", "Unknown"))

        card_type = card.get("humanReadableCardType") or card.get("type", "")
        race = card.get("race", "")
        attr = card.get("attribute", "")

        header_info = f"[{card_type}]"
        if race:
            header_info += f"  •  Race/Property: {race}"
        if attr:
            header_info += f"  •  Attribute: {attr}"
        self.lbl_type_line.setText(header_info)

        stats = []
        if card.get("level") is not None:
            stats.append(f"Level/Rank: {card.get('level')}")
        if card.get("scale") is not None:
            stats.append(f"Pendulum Scale: {card.get('scale')}")
        if card.get("atk") is not None:
            stats.append(f"ATK: {card.get('atk')}")
        if card.get("def") is not None:
            stats.append(f"DEF: {card.get('def')}")
        if card.get("linkval") is not None:
            stats.append(f"Link: {card.get('linkval')}")
            if card.get("linkmarkers"):
                stats.append(f"Markers: [{', '.join(card.get('linkmarkers'))}]")

        self.lbl_stats.setText("   |   ".join(stats) if stats else "")
        self.txt_desc.type_text(card.get("desc", ""), 0)

        self.current_artworks = resolve_artwork_paths(card)
        self.current_art_index = 0

        if len(self.current_artworks) > 1:
            self.update_artwork_view()
        else:
            self.lbl_art_counter.setText("Artwork 1 / 1" if self.current_artworks else "Artwork 0 / 0")
            self.btn_prev_art.setEnabled(False)
            self.btn_next_art.setEnabled(False)
            path = self.current_artworks[0] if self.current_artworks else ""
            self.card_canvas.set_image(path)

        self.update_card_id_and_link()

    def update_card_id_and_link(self):
        if not self.current_card:
            self.lbl_card_id.setText("Card ID: -")
            self.lbl_image_link.setText("")
            return

        base_id = str(self.current_card.get("id", "Unknown"))
        card_images = self.current_card.get("card_images", [])

        if card_images and self.current_art_index < len(card_images):
            img_obj = card_images[self.current_art_index]
            art_id = str(img_obj.get("id", base_id))
            img_url = img_obj.get("image_url") or f"https://images.ygoprodeck.com/images/cards/{art_id}.jpg"
        else:
            art_id = base_id
            img_url = f"https://images.ygoprodeck.com/images/cards/{base_id}.jpg"

        if art_id != base_id:
            self.lbl_card_id.setText(f"Card ID: {base_id} (Artwork ID: {art_id})")
        else:
            self.lbl_card_id.setText(f"Card ID: {base_id}")

        self.lbl_image_link.setText(
            f'<a href="{img_url}" style="color: #58a6ff; text-decoration: underline;">View Online Artwork</a>'
        )

    def update_artwork_view(self):
        total = len(self.current_artworks)
        self.lbl_art_counter.setText(f"Artwork {self.current_art_index + 1} / {total}")
        self.btn_prev_art.setEnabled(self.current_art_index > 0)
        self.btn_next_art.setEnabled(self.current_art_index < total - 1)
        self.card_canvas.set_image(self.current_artworks[self.current_art_index])
        self.update_card_id_and_link()

    def prev_artwork(self):
        if self.current_art_index > 0:
            self.current_art_index -= 1
            self.update_artwork_view()

    def next_artwork(self):
        if self.current_art_index < len(self.current_artworks) - 1:
            self.current_art_index += 1
            self.update_artwork_view()