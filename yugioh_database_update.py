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
    IMG_THUMB_FOLDER
except NameError:
    IMG_THUMB_FOLDER = "cards_images_thumbnail"

try:
    API_URL
except NameError:
    API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"

YUGIPEDIA_API_URL = "https://yugipedia.com/api.php"


class DatabaseUpdateWorker(QThread):
    """
    Background worker that updates the card catalog, artwork cache, and thumbnails
    without freezing the PySide6 UI.

    Supports two operational modes:
      - 'fast': Syncs catalog JSONs; skips cards whose artworks are already up to date.
      - 'full': Forces complete redownload, Yugipedia query, and re-fusion of all images.
    """
    status_changed = Signal(str)
    progress_changed = Signal(int, int)        # (current, total)
    sync_finished = Signal(list, int, int)     # (cards_data, downloaded_images, errors)
    error_occurred = Signal(str)

    def __init__(self, max_workers: int = 4, timeout: int = 30, art_box: tuple = None, parent=None):
        super().__init__(parent)
        self.max_workers = max_workers
        self.timeout = timeout
        self.art_box = art_box or DEFINE.top_left
        self.mode = "fast"  # 'fast' or 'full'
        
        self.log_lock = Lock()
        self.yp_lock = Lock()
        self.executor = None
        self.http_session = self._create_session()

        # Circuit Breaker attributes for Yugipedia
        self.yp_circuit_broken = False
        self.consecutive_yp_failures = 0

    # =========================================================================
    # NETWORKING, LOGGING & KILL-SWITCH
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

    def requestInterruption(self):
        """
        Kill-switch handler: signals interruption, terminates queued executor tasks,
        and closes the HTTP session immediately to release socket reads.
        """
        super().requestInterruption()
        if self.executor:
            try:
                self.executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
        if self.http_session:
            try:
                self.http_session.close()
            except Exception:
                pass

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
        Downloads card scans from YGOPRODeck saved as JPEG (quality=92).
        Returns a tuple of (downloaded_full_paths, download_count).
        """
        card_id = str(card_data.get("id"))
        images = card_data.get("card_images", [])
        target_images = images if fetch_all else images[:1]

        downloaded_paths = []
        new_downloads = 0

        for img_obj in target_images:
            if self.isInterruptionRequested():
                break

            img_id = str(img_obj.get("id", card_id))
            full_dest = os.path.join(IMG_FULL_FOLDER, f"{card_id}_{img_id}.jpg")

            # 1. Full Image Scan
            if not os.path.isfile(full_dest) or force:
                url = img_obj.get("image_url") or f"https://images.ygoprodeck.com/images/cards/{img_id}.jpg"
                try:
                    res = self.http_session.get(url, timeout=self.timeout)
                    if res.status_code == 200:
                        with Image.open(io.BytesIO(res.content)) as f_img:
                            f_img.convert("RGB").save(full_dest, "JPEG", quality=92, optimize=True)
                        new_downloads += 1
                        downloaded_paths.append(full_dest)
                except Exception as e:
                    self._log_error(f"YGOPRO Full DL Fail: {card_id}_{img_id} - {e}")
            else:
                downloaded_paths.append(full_dest)

            # 2. Cropped Artwork (Standardized to 624x624 JPEG)
            if fetch_crops:
                crop_dest = os.path.join(IMG_CROP_FOLDER, f"{card_id}_{img_id}.jpg")
                if not os.path.isfile(crop_dest) or force:
                    crop_url = (
                        img_obj.get("image_url_cropped")
                        or f"https://images.ygoprodeck.com/images/cards_cropped/{img_id}.jpg"
                    )
                    try:
                        res = self.http_session.get(crop_url, timeout=self.timeout)
                        if res.status_code == 200:
                            with Image.open(io.BytesIO(res.content)) as c_img:
                                c_img.convert("RGB").resize(
                                    (624, 624), Image.Resampling.LANCZOS
                                ).save(crop_dest, "JPEG", quality=92, optimize=True)
                            new_downloads += 1
                    except Exception as e:
                        self._log_error(f"YGOPRO Crop DL Fail: {card_id}_{img_id} - {e}")

        return downloaded_paths, new_downloads

    # =========================================================================
    # YUGIPEDIA ARTWORK DISCOVERY & CIRCUIT BREAKER
    # =========================================================================

    def _check_yugipedia_health(self) -> bool:
        """Lightweight pre-flight probe to verify Yugipedia availability."""
        try:
            res = self.http_session.get(
                YUGIPEDIA_API_URL,
                params={"action": "query", "meta": "siteinfo", "format": "json"},
                timeout=10
            )
            return res.status_code == 200
        except Exception as e:
            self._log_error(f"Yugipedia Pre-flight Check Failed: {e}")
            return False

    def _record_yp_failure(self, err_msg: str):
        """Registers a failure and trips the circuit breaker if consecutive failures exceed 5."""
        self._log_error(err_msg)
        with self.yp_lock:
            self.consecutive_yp_failures += 1
            if self.consecutive_yp_failures >= 5 and not self.yp_circuit_broken:
                self.yp_circuit_broken = True
                breaker_msg = (
                    "Yugipedia failure threshold reached (5 consecutive errors). "
                    "Circuit breaker tripped: skipping external Yugipedia queries for remaining cards."
                )
                self._log_error(breaker_msg)
                self.status_changed.emit("Yugipedia offline. Falling back to base cards...")

    def fetch_yugipedia_artworks(self, card_name: str) -> list[dict]:
        """Scans Card_Artworks:{Card_Name} on Yugipedia with circuit-breaker protection."""
        if self.yp_circuit_broken:
            return []

        sanitized_name = card_name.strip().replace(" ", "_")
        page_title = f"Card_Artworks:{sanitized_name}"

        params = {
            "action": "query",
            "titles": page_title,
            "prop": "images",
            "format": "json"
        }
        try:
            res = self.http_session.get(YUGIPEDIA_API_URL, params=params, timeout=20)
            if res.status_code != 200:
                raise requests.HTTPError(f"HTTP {res.status_code}")
            pages = res.json().get("query", {}).get("pages", {})
            with self.yp_lock:
                self.consecutive_yp_failures = 0
        except Exception as e:
            self._record_yp_failure(f"Yugipedia Query Fail: {card_name} - {e}")
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
            info_res = self.http_session.get(YUGIPEDIA_API_URL, params=info_params, timeout=20)
            if info_res.status_code != 200:
                raise requests.HTTPError(f"HTTP {info_res.status_code}")
            pages_info = info_res.json().get("query", {}).get("pages", {})
            with self.yp_lock:
                self.consecutive_yp_failures = 0
        except Exception as e:
            self._record_yp_failure(f"Yugipedia ImageInfo Fail: {card_name} - {e}")
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
            full_path = os.path.join(IMG_FULL_FOLDER, f"{cid}_{art_id}.jpg")
            if not os.path.isfile(full_path):
                return False

            if is_pendulum or art_id.startswith("yp_crop_"):
                crop_path = os.path.join(IMG_CROP_FOLDER, f"{cid}_{art_id}.jpg")
                if not os.path.isfile(crop_path):
                    return False

        return True

    # =========================================================================
    # DECOUPLED THUMBNAIL GENERATION
    # =========================================================================

    def generate_thumbnails(self, force: bool = False) -> int:
        """
        Independent task that creates 38x55 thumbnails in IMG_THUMB_FOLDER
        from all available card scans in IMG_FULL_FOLDER.
        Thumbnails remain in lossless PNG format.
        """
        os.makedirs(IMG_THUMB_FOLDER, exist_ok=True)
        full_files = [f for f in os.listdir(IMG_FULL_FOLDER) if f.endswith(".jpg") or f.endswith(".png")]
        total = len(full_files)
        if total == 0:
            return 0

        self.status_changed.emit("Generating thumbnails...")
        self.progress_changed.emit(0, total)

        created_count = 0
        for idx, filename in enumerate(full_files, start=1):
            if self.isInterruptionRequested():
                break

            stem = Path(filename).stem
            thumb_path = os.path.join(IMG_THUMB_FOLDER, f"{stem}.png")

            if not os.path.isfile(thumb_path) or force:
                src_path = os.path.join(IMG_FULL_FOLDER, filename)
                try:
                    with Image.open(src_path) as img:
                        thumb = img.convert("RGB").resize((38, 55), Image.Resampling.BILINEAR)
                        thumb.save(thumb_path, "PNG")
                    created_count += 1
                except Exception as e:
                    self._log_error(f"Thumbnail Fail: {filename} - {e}")

            if idx % 100 == 0 or idx == total:
                self.progress_changed.emit(idx, total)

        return created_count

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
        for folder in [JSON_FOLDER, IMG_FULL_FOLDER, IMG_CROP_FOLDER, IMG_THUMB_FOLDER]:
            os.makedirs(folder, exist_ok=True)

        is_full_sync = (self.mode == "full")
        self.yp_circuit_broken = False
        self.consecutive_yp_failures = 0

        # Pre-flight health check on Yugipedia
        if not self._check_yugipedia_health():
            self.yp_circuit_broken = True
            msg = "Yugipedia pre-flight health probe failed. Running in YGOPRODeck-only mode."
            self._log_error(msg)
            self.status_changed.emit("Yugipedia unavailable. Running fallback mode...")

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
        downloaded_count = 0
        error_count = 0
        completed_tasks = 0
        progress_lock = Lock()

        # =====================================================================
        # PHASE 1: WORKER TASK EXECUTION PER CARD (FETCH & FUSE)
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
                # CASE 2: PENDULUM MONSTERS (Fetch EVERYTHING from YGOPRODeck)
                if is_pendulum:
                    _, new_dls = self.ensure_ygopro_images(
                        card, fetch_all=True, fetch_crops=True, force=is_full_sync
                    )
                    with progress_lock:
                        downloaded_count += new_dls
                    card["yp_synced"] = True
                    self._save_card_json(card)

                # CASE 1 & 3: NORMAL & LINK MONSTERS (Base Template + Fusion)
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

                        # Only mark as synced if Yugipedia was actually reachable and had no variants
                        if not self.yp_circuit_broken:
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
                                    ext_dest = os.path.join(IMG_FULL_FOLDER, f"{cid}_{art_id}.jpg")

                                    if not os.path.isfile(ext_dest) or is_full_sync:
                                        res = self.http_session.get(url, timeout=self.timeout)
                                        if res.status_code == 200:
                                            with Image.open(io.BytesIO(res.content)) as ea_img:
                                                ea_img.convert("RGB").save(ext_dest, "JPEG", quality=92, optimize=True)
                                            with progress_lock:
                                                downloaded_count += 1
                                    self.register_in_json(card, art_id)

                                # Case 1B: Square Cropped Illustration -> Composite
                                elif art_type == "crop":
                                    art_id = f"yp_crop_{idx}"
                                    std_crop_path = os.path.join(IMG_CROP_FOLDER, f"{cid}_{art_id}.jpg")
                                    fused_out_path = os.path.join(IMG_FULL_FOLDER, f"{cid}_{art_id}.jpg")

                                    need_crop = not os.path.isfile(std_crop_path) or is_full_sync
                                    need_fused = not os.path.isfile(fused_out_path) or is_full_sync

                                    if need_crop or need_fused:
                                        res = self.http_session.get(url, timeout=self.timeout)
                                        if res.status_code == 200:
                                            with Image.open(io.BytesIO(res.content)) as raw_crop:
                                                crop_624 = raw_crop.convert("RGB").resize(
                                                    (624, 624), Image.Resampling.LANCZOS
                                                )
                                                crop_624.save(std_crop_path, "JPEG", quality=92, optimize=True)

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

                                            fused_img.convert("RGB").save(fused_out_path, "JPEG", quality=92, optimize=True)
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

            time.sleep(0.02)

        if total_tasks > 0:
            sync_label = "Overwriting" if is_full_sync else "Syncing"
            self.status_changed.emit(f"{sync_label} {total_tasks} cards...")
            self.progress_changed.emit(0, total_tasks)

            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
            try:
                futures = [self.executor.submit(_process_card_task, c) for c in cards_to_process]
                for future in concurrent.futures.as_completed(futures):
                    if self.isInterruptionRequested():
                        self.executor.shutdown(wait=False, cancel_futures=True)
                        break
            finally:
                if self.isInterruptionRequested():
                    self.executor.shutdown(wait=False, cancel_futures=True)
                else:
                    self.executor.shutdown(wait=True)
                self.executor = None

        if self.isInterruptionRequested():
            return

        # =====================================================================
        # PHASE 2: DECOUPLED THUMBNAIL BAKING (PNG)
        # =====================================================================
        self.generate_thumbnails(force=is_full_sync)

        if not self.isInterruptionRequested():
            self.status_changed.emit("Sync complete.")
            self.sync_finished.emit(cards_data, downloaded_count, error_count)