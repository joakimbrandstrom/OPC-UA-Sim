"""CSV data management utilities."""

from __future__ import annotations

import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from . import config


class CSVDataManager:
    """Manage CSV files used by the OPC UA simulator.

    The manager is responsible for tracking the active CSV file, saving
    uploads from the web UI, and providing thread-safe access to the
    underlying :class:`pandas.DataFrame` instances.
    """

    def __init__(self, data_dir: Path | None = None, *, time_column: str | None = None,
                 default_file: str | None = None) -> None:
        self._lock = threading.RLock()
        self.data_dir = (data_dir or config.DEFAULT_DATA_DIR).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.time_column = (time_column or config.DEFAULT_TIME_COLUMN).lower()
        self._cache_path: Optional[Path] = None
        self._cache_mtime: Optional[float] = None
        self._cached_df: Optional[pd.DataFrame] = None

        default_file = default_file or config.DEFAULT_SAMPLE_FILE
        self._active_file: Optional[Path] = None
        if default_file:
            self._active_file = self._prepare_initial_file(default_file)

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------
    def _prepare_initial_file(self, filename: str) -> Optional[Path]:
        candidate = Path(filename)
        if not candidate.is_absolute():
            candidate = self.data_dir / candidate

        if candidate.exists():
            return candidate

        # Fall back to bundled sample data if available
        bundled = Path(__file__).resolve().parent.parent / "data" / filename
        if bundled.exists():
            candidate.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(bundled, candidate)
            return candidate

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def active_file(self) -> Optional[Path]:
        with self._lock:
            return self._active_file

    def set_active_file(self, filename: str | Path) -> Path:
        """Set the active CSV file by name.

        Parameters
        ----------
        filename:
            Either the file name relative to the data directory or an
            absolute :class:`~pathlib.Path` instance.
        """

        path = Path(filename)
        if not path.is_absolute():
            path = self.data_dir / path

        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")
        if not path.is_relative_to(self.data_dir):
            raise ValueError("CSV file must reside inside the data directory")

        with self._lock:
            self._active_file = path
            self._invalidate_cache()

        return path

    def list_datasets(self) -> List[Path]:
        """Return a sorted list of available CSV files."""

        return sorted(self.data_dir.glob("*.csv"))

    def save_upload(self, file: FileStorage) -> Path:
        """Persist an uploaded CSV file and make it the active dataset."""

        if not file.filename:
            raise ValueError("Uploaded file must have a filename")

        filename = secure_filename(file.filename)
        if not filename.lower().endswith(".csv"):
            raise ValueError("Only CSV files are supported")

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        target_name = f"{Path(filename).stem}_{timestamp}.csv"
        target_path = (self.data_dir / target_name).resolve()

        if not target_path.is_relative_to(self.data_dir):
            raise ValueError("Upload path resolves outside the data directory")

        with self._lock:
            file.save(target_path)
            self._active_file = target_path
            self._invalidate_cache()

        return target_path

    def get_dataframe(self) -> pd.DataFrame:
        """Return the active CSV file as a :class:`pandas.DataFrame`."""

        path = self.active_file
        if path is None:
            raise FileNotFoundError("No active CSV file configured")
        if not path.exists():
            raise FileNotFoundError(f"Active CSV file does not exist: {path}")

        mtime = path.stat().st_mtime
        with self._lock:
            if self._cache_path == path and self._cache_mtime == mtime and self._cached_df is not None:
                return self._cached_df.copy()

            df = pd.read_csv(path).fillna(0)
            self._cache_path = path
            self._cache_mtime = mtime
            self._cached_df = df
            return df.copy()

    def iter_value_columns(self, df: pd.DataFrame) -> Iterable[str]:
        """Yield the columns that should be exposed as OPC UA variables."""

        for column in df.columns:
            if column.lower() != self.time_column:
                yield column

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _invalidate_cache(self) -> None:
        self._cache_path = None
        self._cache_mtime = None
        self._cached_df = None
