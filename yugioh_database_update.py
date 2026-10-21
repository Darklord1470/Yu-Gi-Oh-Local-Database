import os
import io
import re
import json
import time
import requests
import numpy as np
from PIL import Image
from pathlib import Path
from threading import Lock
import concurrent.futures
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from PySide6.QtCore import QThread, Signal

# Import globals and environment constants
from yugioh_database_global_func import *

# Defensive fallback definitions for folder structure and API endpoints
try:
    JSON_FOLDER
except NameError:
    JSON_FOLDER = "cards_data"

try:
    IMG_FULL_FOLDER
except NameError:
    IMG_FULL_FOLDER = "cards_images_full"

try:
    IMG_CROP_FOLDER
except NameError:
    IMG_CROP_FOLDER = "cards_images_artwork"

try:
    API_URL
except NameError:
    API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

YUGIPEDIA_API_URL = "https://yugipedia.com/api.php"


class DatabaseUpdateWorker(QThread):
    """
    Background worker that updates the card catalog and artwork cache
    without freezing the PySide6 UI.

    Supports two operational modes:
      - 'fast': Syncs catalog JSONs; skips cards whose artworks are already up to date.
      - 'full': Forces complete redownload, Yugipedia query, and re-fusion of all images.
    """
    status_changed = Signal(str)
    progress_changed = Signal(int, int)        # (current, total)
    sync_finished = Signal(list, int, int)     # (cards_data, downloaded_images, errors)
    error_occurred = Signal(str)

    def __init__(self, max_workers: int = 4, timeout: int = 30, art_box: Tuple[int] = None, parent=None):
        super().__init__(parent)
        self.max_workers = max_workers
        self.timeout = timeout
        self.art_box = art_box or DEFINE.top_left
        self.mode = "fast"  # 'fast' or 'full'
        self.log_lock = Lock()
        self.http_session = self._create_session()

    # =========================================================================
    # NETWORKING & ERROR LOGGING
    # =========================================================================

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "YuGiOhLocalDatabase/2.0 (Artwork Sync Pipeline; Desktop Client)"
        })
        retries = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=12, pool_maxsize=12)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _log_error(self, msg: str):
        with self.log_lock:
            with open("ERR.txt", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    # =========================================================================
    # CORE ARRAY COMPOSITING
    # =========================================================================

    def _collapse_artwork_into_image(self, full_img: Image.Image, artwork: Image.Image, x: int, y: int) -> Image.Image:
        """Directly overwrites the base image's raw array slice with the artwork's array values."""
        base_arr = np.array(full_img)
        mark_arr = np.array(artwork.convert(full_img.mode))
        h, w = mark_arr.shape[:2]

        base_arr[y : y + h, x : x + w] = mark_arr
        return Image.fromarray(base_arr)

    def _collapse_link_artwork_into_image(
        self, full_img: Image.Image, artwork: Image.Image, x: int, y: int, corner_cut: int = 23
    ) -> Image.Image:
        """
        Overwrites the base image's art frame while preserving the 4 diagonal Link Markers.
        Pixels within `corner_cut` distance from the 4 corners remain unchanged.
        """
        base_arr = np.array(full_img)
        mark_arr = np.array(artwork.convert(full_img.mode))
        h, w = mark_arr.shape[:2]

        slice_base = base_arr[y : y + h, x : x + w]

        # Generate boolean mask for the 4 diagonal arrow corners
        rows, cols = np.ogrid[:h, :w]
        tl = (rows + cols) < corner_cut
        tr = (rows + (w - 1 - cols)) < corner_cut
        bl = ((h - 1 - rows) + cols) < corner_cut
        br = ((h - 1 - rows) + (w - 1 - cols)) < corner_cut
        arrow_mask = tl | tr | bl | br

        # Preserve original base pixels on arrow corners, apply artwork everywhere else
        blended = np.where(arrow_mask[:, :, None], slice_base, mark_arr)
        base_arr[y : y + h, x : x + w] = blended
        return Image.fromarray(base_arr)

    # =========================================================================
    # YGOPRODECK ASSET MANAGEMENT
    # =========================================================================

    def ensure_ygopro_images(
        self, card_data: dict, fetch_all: bool = False, fetch_crops: bool = False, force: bool = False
    ) -> tuple[list[str], int]:
        """
        Downloads card scans from YGOPRODeck saved losslessly as PNG.
        Returns a tuple of (downloaded_full_paths, download_count).
        """
        card_id = str(card_data.get("id"))
        images = card_data.get("card_images", [])
        target_images = images if fetch_all else images[:1]

        downloaded_paths = []
        new_downloads = 0

        for img_obj in target_images:
            img_id = str(img_obj.get("id", card_id))
            full_dest = os.path.join(IMG_FULL_FOLDER, f"{card_id}_{img_id}.png")

            # 1. Full Image Scan
            if not os.path.isfile(full_dest) or force:
                url = img_obj.get("image_url") or f"https://images.ygoprodeck.com/images/cards/{img_id}.jpg"
                try:
                    res = self.http_session.get(url, timeout=self.timeout)
                    if res.status_code == 200:
                        with Image.open(io.BytesIO(res.content)) as f_img:
                            f_img.convert("RGB").save(full_dest, "PNG")
                        new_downloads += 1
                        downloaded_paths.append(full_dest)
                except Exception as e:
                    self._log_error(f"YGOPRO Full DL Fail: {card_id}_{img_id} - {e}")
            else:
                downloaded_paths.append(full_dest)

            # 2. Cropped Artwork (Standardized to 624x624 PNG)
            if fetch_crops:
                crop_dest = os.path.join(IMG_CROP_FOLDER, f"{card_id}_{img_id}.png")
                if not os.path.isfile(crop_dest) or force:
                    crop_url = (
                        img_obj.get("image_url_cropped")
                        or f"https://images.ygoprodeck.com/images/cards_cropped/{img_id}.jpg"
                    )
                    try:
                        res = self.http_session.get(crop_url, timeout=self.timeout)
                        if res.status_code == 200:
                            with Image.open(io.BytesIO(res.content)) as c_img:
                                c_img.convert("RGBA").resize(
                                    (624, 624), Image.Resampling.LANCZOS
                                ).save(crop_dest, "PNG")
                            new_downloads += 1
                    except Exception as e:
                        self._log_error(f"YGOPRO Crop DL Fail: {card_id}_{img_id} - {e}")

        return downloaded_paths, new_downloads

    # =========================================================================
    # YUGIPEDIA ARTWORK DISCOVERY
    # =========================================================================

    def fetch_yugipedia_artworks(self, card_name: str) -> list[dict]:
        """Scans Card_Artworks:{Card_Name} on Yugipedia and returns direct URLs."""
        sanitized_name = card_name.strip().replace(" ", "_")
        page_title = f"Card_Artworks:{sanitized_name}"

        params = {
            "action": "query",
            "titles": page_title,
            "prop": "images",
            "format": "json"
        }
        try:
            res = self.http_session.get(YUGIPEDIA_API_URL, params=params, timeout=20).json()
            pages = res.get("query", {}).get("pages", {})
        except Exception as e:
            self._log_error(f"Yugipedia Query Fail: {card_name} - {e}")
            return []

        file_titles = []
        for page_id, page_data in pages.items():
            if page_id == "-1":
                return []
            for img in page_data.get("images", []):
                file_titles.append(img.get("title"))

        matched = []
        for title in file_titles:
            clean = title.replace("File:", "").strip()
            # Extended / Overframe Artworks
            if re.search(r"-(ea|orr)\.[a-zA-Z0-9]+$", clean, re.IGNORECASE):
                matched.append((title, clean, "extended"))
            # Cropped Artwork Illustrations
            elif re.search(r"artwork", clean, re.IGNORECASE):
                matched.append((title, clean, "crop"))

        if not matched:
            return []

        # Batch resolve URLs via MediaWiki imageinfo
        titles_param = "|".join(t[0] for t in matched)
        info_params = {
            "action": "query",
            "titles": titles_param,
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json"
        }
        try:
            info_res = self.http_session.get(YUGIPEDIA_API_URL, params=info_params, timeout=20).json()
            pages_info = info_res.get("query", {}).get("pages", {})
        except Exception as e:
            self._log_error(f"Yugipedia ImageInfo Fail: {card_name} - {e}")
            return []

        url_lookup = {}
        for _, p_val in pages_info.items():
            t_name = p_val.get("title", "")
            iinfo = p_val.get("imageinfo", [])
            if iinfo and iinfo[0].get("url"):
                url_lookup[t_name] = iinfo[0].get("url")

        resolved = []
        for full_title, clean, art_type in matched:
            if full_title in url_lookup:
                resolved.append({
                    "filename": clean,
                    "url": url_lookup[full_title],
                    "type": art_type
                })

        return resolved

    # =========================================================================
    # METADATA SYNC & REGISTRATION HELPERS
    # =========================================================================

    def _save_card_json(self, card_data: dict):
        cid = str(card_data.get("id"))
        json_path = os.path.join(JSON_FOLDER, f"{cid}.json")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(card_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._log_error(f"JSON Write Fail: {cid} - {e}")

    def register_in_json(self, card_data: dict, new_art_id: str):
        """Registers a new artwork ID into in-memory card_data and disk JSON."""
        images = card_data.setdefault("card_images", [])
        if not any(str(img.get("id")) == str(new_art_id) for img in images):
            images.append({"id": new_art_id})

    def _is_card_up_to_date(self, card_data: dict) -> bool:
        """Determines if a card already has all required images on disk for fast sync."""
        if not card_data.get("yp_synced"):
            return False

        cid = str(card_data.get("id", ""))
        ctype = card_data.get("type", "").lower()
        ftype = card_data.get("frameType", "").lower()
        is_pendulum = "pendulum" in ctype or "pendulum" in ftype

        for img_obj in card_data.get("card_images", []):
            art_id = str(img_obj.get("id", cid))
            full_path = os.path.join(IMG_FULL_FOLDER, f"{cid}_{art_id}.png")
            if not os.path.isfile(full_path):
                return False

            if is_pendulum or art_id.startswith("yp_crop_"):
                crop_path = os.path.join(IMG_CROP_FOLDER, f"{cid}_{art_id}.png")
                if not os.path.isfile(crop_path):
                    return False

        return True

    # =========================================================================
    # WORKER CONTROLS & MAIN EXECUTION
    # =========================================================================

    def sync_quick(self) -> bool:
        """Starts an incremental sync (missing images only). Returns False if already running."""
        if self.isRunning():
            return False
        self.mode = "fast"
        self.start()
        return True

    def sync_full(self) -> bool:
        """Starts a full sync (forces redownload and re-fusion of all images)."""
        if self.isRunning():
            return False
        self.mode = "full"
        self.start()
        return True

    def run(self):
        for folder in [JSON_FOLDER, IMG_FULL_FOLDER, IMG_CROP_FOLDER]:
            os.makedirs(folder, exist_ok=True)

        is_full_sync = (self.mode == "full")

        # 1. Fetch Remote Database Catalog from YGOPRODeck
        self.status_changed.emit(f"{self.mode.upper()} Fetching...")
        try:
            res = self.http_session.get(API_URL, timeout=60)
            res.raise_for_status()
            cards_data = res.json().get("data", [])
        except requests.RequestException as e:
            err_msg = f"Network connection error while fetching database: {e}"
            self._log_error(err_msg)
            self.error_occurred.emit(err_msg)
            return

        total_cards = len(cards_data)
        if total_cards == 0:
            self.error_occurred.emit("Received empty card catalog from server.")
            return

        # 2. Sync Local Card JSONs (Preserving existing Yugipedia entries in fast mode)
        self.status_changed.emit(f"Syncing {total_cards}...")
        for idx, card in enumerate(cards_data, start=1):
            if self.isInterruptionRequested():
                return

            card_id = str(card.get("id", ""))
            if not card_id:
                continue

            json_path = os.path.join(JSON_FOLDER, f"{card_id}.json")
            if not is_full_sync and os.path.isfile(json_path):
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        local_json = json.load(f)

                    # Preserve Yugipedia artworks and sync flag across updates
                    existing_yp = [
                        img for img in local_json.get("card_images", [])
                        if str(img.get("id", "")).startswith("yp_")
                    ]
                    current_ids = {str(img.get("id", "")) for img in card.get("card_images", [])}
                    for yp_img in existing_yp:
                        if str(yp_img.get("id", "")) not in current_ids:
                            card.setdefault("card_images", []).append(yp_img)

                    if local_json.get("yp_synced"):
                        card["yp_synced"] = True
                except Exception:
                    pass

            self._save_card_json(card)

            if idx % 50 == 0:
                time.sleep(0.001)

        # 3. Identify Cards Requiring Image Sync / Fusion
        self.status_changed.emit("Analyzing artwork...")
        if is_full_sync:
            cards_to_process = cards_data
        else:
            cards_to_process = [c for c in cards_data if not self._is_card_up_to_date(c)]

        total_tasks = len(cards_to_process)
        if total_tasks == 0:
            self.status_changed.emit("Already up to date.")
            self.sync_finished.emit(cards_data, 0, 0)
            return

        sync_label = "Overwriting" if is_full_sync else "Syncing"
        self.status_changed.emit(f"{sync_label} {total_tasks} cards...")
        self.progress_changed.emit(0, total_tasks)

        downloaded_count = 0
        error_count = 0
        completed_tasks = 0
        progress_lock = Lock()

        # =====================================================================
        # WORKER TASK EXECUTION PER CARD
        # =====================================================================
        def _process_card_task(card):
            nonlocal downloaded_count, error_count, completed_tasks
            if self.isInterruptionRequested():
                return

            cid = str(card.get("id", ""))
            cname = card.get("name", "Unknown")
            ctype = card.get("type", "").lower()
            ftype = card.get("frameType", "").lower()

            is_pendulum = "pendulum" in ctype or "pendulum" in ftype
            is_link = "link" in ctype or "link" in ftype

            try:
                # -------------------------------------------------------------
                # CASE 2: PENDULUM MONSTERS (Fetch EVERYTHING from YGOPRODeck)
                # -------------------------------------------------------------
                if is_pendulum:
                    _, new_dls = self.ensure_ygopro_images(
                        card, fetch_all=True, fetch_crops=True, force=is_full_sync
                    )
                    with progress_lock:
                        downloaded_count += new_dls
                    card["yp_synced"] = True
                    self._save_card_json(card)

                # -------------------------------------------------------------
                # CASE 1 & 3: NORMAL & LINK MONSTERS (Base Template + Fusion)
                # -------------------------------------------------------------
                else:
                    # Step A: Ensure base card scan template exists
                    base_paths, new_base_dls = self.ensure_ygopro_images(
                        card, fetch_all=False, fetch_crops=False, force=is_full_sync
                    )
                    with progress_lock:
                        downloaded_count += new_base_dls

                    if not base_paths:
                        raise RuntimeError(f"Base template unavailable for card {cid}")

                    base_template_path = base_paths[0]

                    # Step B: Query Yugipedia for artwork variants
                    yp_assets = self.fetch_yugipedia_artworks(cname)

                    if not yp_assets:
                        # Fallback: Save YGOPRODeck base crop if no Yugipedia assets exist
                        _, new_crop_dls = self.ensure_ygopro_images(
                            card, fetch_all=False, fetch_crops=True, force=is_full_sync
                        )
                        with progress_lock:
                            downloaded_count += new_crop_dls
                        card["yp_synced"] = True
                        self._save_card_json(card)

                    else:
                        with Image.open(base_template_path) as base_img:
                            base_full = base_img.convert("RGB")
                            if base_full.size != (813, 1185):
                                base_full = base_full.resize((813, 1185), Image.Resampling.LANCZOS)

                            for idx, asset in enumerate(yp_assets, start=1):
                                if self.isInterruptionRequested():
                                    return

                                art_type = asset["type"]
                                url = asset["url"]

                                # Case 1A: Extended Art / Overframe -> Full-card scan
                                if art_type == "extended":
                                    art_id = f"yp_ea_{idx}"
                                    ext_dest = os.path.join(IMG_FULL_FOLDER, f"{cid}_{art_id}.png")

                                    if not os.path.isfile(ext_dest) or is_full_sync:
                                        res = self.http_session.get(url, timeout=self.timeout)
                                        if res.status_code == 200:
                                            with Image.open(io.BytesIO(res.content)) as ea_img:
                                                ea_img.convert("RGB").save(ext_dest, "PNG")
                                            with progress_lock:
                                                downloaded_count += 1
                                    self.register_in_json(card, art_id)

                                # Case 1B: Square Cropped Illustration -> Composite
                                elif art_type == "crop":
                                    art_id = f"yp_crop_{idx}"
                                    std_crop_path = os.path.join(IMG_CROP_FOLDER, f"{cid}_{art_id}.png")
                                    fused_out_path = os.path.join(IMG_FULL_FOLDER, f"{cid}_{art_id}.png")

                                    need_crop = not os.path.isfile(std_crop_path) or is_full_sync
                                    need_fused = not os.path.isfile(fused_out_path) or is_full_sync

                                    if need_crop or need_fused:
                                        res = self.http_session.get(url, timeout=self.timeout)
                                        if res.status_code == 200:
                                            with Image.open(io.BytesIO(res.content)) as raw_crop:
                                                crop_624 = raw_crop.convert("RGBA").resize(
                                                    (624, 624), Image.Resampling.LANCZOS
                                                )
                                                crop_624.save(std_crop_path, "PNG")

                                            box_x = self.art_box[0]
                                            box_y = self.art_box[1]

                                            if is_link:
                                                fused_img = self._collapse_link_artwork_into_image(
                                                    base_full, crop_624, box_x, box_y, corner_cut=23
                                                )
                                            else:
                                                fused_img = self._collapse_artwork_into_image(
                                                    base_full, crop_624, box_x, box_y
                                                )

                                            fused_img.convert("RGB").save(fused_out_path, "PNG")
                                            with progress_lock:
                                                downloaded_count += 1

                                    self.register_in_json(card, art_id)

                        card["yp_synced"] = True
                        self._save_card_json(card)

            except Exception as e:
                with progress_lock:
                    error_count += 1
                self._log_error(f"Task Failed: {cname} ({cid}) - {e}")

            with progress_lock:
                completed_tasks += 1
                if completed_tasks % 5 == 0 or completed_tasks == total_tasks:
                    self.progress_changed.emit(completed_tasks, total_tasks)

            time.sleep(0.02)  # Respect polite request concurrency limits

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(_process_card_task, c) for c in cards_to_process]
            for future in concurrent.futures.as_completed(futures):
                if self.isInterruptionRequested():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

        self.sync_finished.emit(cards_data, downloaded_count, error_count)
