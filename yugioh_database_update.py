from yugioh_database_global_func import *

class DatabaseUpdateWorker(QThread):
    """
    Background worker that updates the card catalog and artwork cache
    without freezing the PySide6 UI.

    Supports two operational modes:
      - 'fast': Syncs all JSONs; only downloads missing images.
      - 'full': Syncs all JSONs; forces redownload and overwrite of all images.
    """
    status_changed = Signal(str)
    progress_changed = Signal(int, int)        # (current, total)
    sync_finished = Signal(list, int, int)     # (cards_data, downloaded_images, errors)
    error_occurred = Signal(str)

    def __init__(self, max_workers: int = 4, timeout: int = 30, parent=None):
        super().__init__(parent)
        self.max_workers = max_workers
        self.timeout = timeout
        self.mode = "fast"  # 'fast' or 'full'
        self.log_lock = Lock()
        self.http_session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"User-Agent": "YuGiOhLocalDatabase/2.0"})
        retries = Retry(
            total=3,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _log_error(self, msg: str):
        with self.log_lock:
            with open("ERR.txt", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

    def _download_file(self, url: str, out_path: str):
        res = self.http_session.get(url, timeout=self.timeout)
        res.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(res.content)

    def sync_quick(self) -> bool:
        """Starts an incremental sync (missing images only). Returns False if already running."""
        if self.isRunning():
            return False
        self.mode = "fast"
        self.start()
        return True

    def sync_full(self) -> bool:
        """Starts a full sync (forces download/overwrite of all images). Returns False if already running."""
        if self.isRunning():
            return False
        self.mode = "full"
        self.start()
        return True

    def run(self):
        for folder in [JSON_FOLDER, IMG_FULL_FOLDER, IMG_CROP_FOLDER]:
            os.makedirs(folder, exist_ok=True)

        is_full_sync = (self.mode == "full")

        # 1. Fetch Remote Database Catalog
        self.status_changed.emit(f"Fetching catalog ({self.mode.upper()} mode)...")
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

        # 2. Overwrite / Sync JSON Files (Yielding the GIL every 50 writes to prevent UI stutter)
        self.status_changed.emit(f"Syncing {total_cards} card JSONs...")
        for idx, card in enumerate(cards_data, start=1):
            if self.isInterruptionRequested():
                return
            card_id = str(card.get("id", ""))
            if not card_id:
                continue
            path = os.path.join(JSON_FOLDER, f"{card_id}.json")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(card, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self._log_error(f"JSON SAVE FAILED: Card {card_id} - {e}")

            if idx % 50 == 0:
                time.sleep(0.001)

        # 3. Identify Artwork Tasks
        self.status_changed.emit("Analyzing artwork requirements...")
        cached_crop = set() if is_full_sync else {Path(f).stem for f in os.listdir(IMG_CROP_FOLDER)}
        cached_full = set() if is_full_sync else {Path(f).stem for f in os.listdir(IMG_FULL_FOLDER)}

        download_tasks = []
        for card in cards_data:
            card_id = str(card.get("id", ""))
            card_name = card.get("name", "Unknown")

            for img_obj in card.get("card_images", []):
                img_id = str(img_obj.get("id", ""))
                file_stem = f"{card_id}_{img_id}"

                # Cropped Artwork
                crop_url = img_obj.get("image_url_cropped")
                if crop_url and (is_full_sync or file_stem not in cached_crop):
                    ext = crop_url.split("?")[0].split(".")[-1]
                    out_path = os.path.join(IMG_CROP_FOLDER, f"{file_stem}.{ext}")
                    download_tasks.append((crop_url, out_path, card_name, file_stem, "CROP"))

                # Full Artwork
                full_url = img_obj.get("image_url")
                if full_url and (is_full_sync or file_stem not in cached_full):
                    ext = full_url.split("?")[0].split(".")[-1]
                    out_path = os.path.join(IMG_FULL_FOLDER, f"{file_stem}.{ext}")
                    download_tasks.append((full_url, out_path, card_name, file_stem, "FULL"))

        total_downloads = len(download_tasks)
        if total_downloads == 0:
            self.status_changed.emit("Images already up to date.")
            self.sync_finished.emit(cards_data, 0, 0)
            return

        sync_label = "overwriting" if is_full_sync else "downloading"
        self.status_changed.emit(f"Queue: {sync_label} {total_downloads} images...")
        self.progress_changed.emit(0, total_downloads)

        downloaded_count = 0
        error_count = 0
        progress_lock = Lock()

        def _worker_task(task_info):
            nonlocal downloaded_count, error_count
            if self.isInterruptionRequested():
                return

            url, out_path, card_name, stem, kind = task_info
            try:
                self._download_file(url, out_path)
                with progress_lock:
                    downloaded_count += 1
            except Exception as e:
                with progress_lock:
                    error_count += 1
                self._log_error(f"{kind} FAIL: {card_name} ({stem}) - {e}")

            with progress_lock:
                current_total = downloaded_count + error_count
                if current_total % 10 == 0 or current_total == total_downloads:
                    self.progress_changed.emit(current_total, total_downloads)

            time.sleep(0.05)  # Enforce compliance with the 20 req/s rate limit

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(_worker_task, t) for t in download_tasks]
            for future in concurrent.futures.as_completed(futures):
                if self.isInterruptionRequested():
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

        self.sync_finished.emit(cards_data, downloaded_count, error_count)
