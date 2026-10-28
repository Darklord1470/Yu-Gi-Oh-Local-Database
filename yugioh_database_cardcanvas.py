from yugioh_database_global_imports import *

class CardViewCanvas(QWidget):
    """Bilinear filtered canvas rendering cards at native resolution on High-DPI screens."""
    def __init__(self, parent=None, size_mult: tuple[float,float] = (1.0,1.0)):
        super().__init__(parent)
        self.pixmap = None
        self.img_path = Path()
        self.processed_img = None
        self.img_changed_counter = 0
        self.setFixedSize(int(388*size_mult[0]), int(570*size_mult[1]))
        self.reset_to_default()

    def set_image(self, file_path: str):
        if file_path and os.path.isfile(file_path):
            self.pixmap = QPixmap(file_path)
            self.img_path = Path(file_path)
            self.img_changed_counter += 1
        else:
            self.pixmap = None
        self.update()

    def get_image(self):
        return self.processed_img

    def set_image_from_image(self, image: Image.Image = None):
        if image:
            self.pixmap = toqpixmap(image)
            self.processed_img = image
            self.img_changed_counter += 1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if not self.pixmap or self.pixmap.isNull():
            painter.setPen(QColor("#666677"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Image Available")
            return

        scaled_size = self.pixmap.size().scaled(self.rect().size(), Qt.AspectRatioMode.KeepAspectRatio)
        x = (self.width() - scaled_size.width()) // 2
        y = (self.height() - scaled_size.height()) // 2
        dest_rect = QRect(x, y, scaled_size.width(), scaled_size.height())

        painter.drawPixmap(dest_rect, self.pixmap)

    def reset_to_default(self):
        for default_path in [path for path in os.listdir(IMG_FULL_FOLDER) if "149694341_" in path]:
            candidate_path = os.path.join(IMG_FULL_FOLDER, default_path)

            if os.path.isfile(candidate_path):
                self.set_image(candidate_path)
                break