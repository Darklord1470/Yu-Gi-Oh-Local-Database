from yugioh_database_global_imports_root import *

def sanitize_icon(icon: QIcon, size: QSize = QSize(24, 24)) -> QIcon:
    """Converts icons to 32-bit ARGB to prevent QFusionStyle paint engine warnings."""
    if not icon or icon.isNull():
        return QIcon()
    pm = icon.pixmap(size)
    if pm.isNull():
        return QIcon()
    img = pm.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    clean_pm = QPixmap.fromImage(img)
    sanitized = QIcon()
    sanitized.addPixmap(clean_pm, QIcon.Mode.Normal)
    sanitized.addPixmap(clean_pm, QIcon.Mode.Selected)
    sanitized.addPixmap(clean_pm, QIcon.Mode.Active)
    return sanitized


def is_playable_card(card: dict) -> bool:
    """Discards non-OCG/TCG Skill Cards while keeping them safe in the disk database."""
    card_type = card.get("type", "").lower()
    frame_type = card.get("frameType", "").lower()
    if "skill" in card_type or "skill" in frame_type:
        return False
    return True


def resolve_artwork_paths(card_data: dict) -> list[str]:
    """Finds all full artwork paths supporting composite {card_id}_{img_id} and single {id}."""
    if not os.path.exists(IMG_FULL_FOLDER):
        return []

    card_id = str(card_data.get("id", ""))
    images = card_data.get("card_images", [])
    found_paths = []

    for img in images:
        img_id = str(img.get("id", ""))
        candidates = [f"{card_id}_{img_id}", img_id, card_id]
        match = None
        for stem in candidates:
            for ext in [".jpg", ".jpeg", ".png"]:
                p = os.path.join(IMG_FULL_FOLDER, f"{stem}{ext}")
                if os.path.isfile(p):
                    match = p
                    break
            if match:
                break
        if match and match not in found_paths:
            found_paths.append(match)

    if not found_paths and card_id:
        for ext in [".jpg", ".jpeg", ".png"]:
            p = os.path.join(IMG_FULL_FOLDER, f"{card_id}{ext}")
            if os.path.isfile(p):
                found_paths.append(p)
                break

    return found_paths