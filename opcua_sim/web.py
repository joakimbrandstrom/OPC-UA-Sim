"""Web application for managing CSV datasets."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from flask import Flask, flash, redirect, render_template, request, url_for

from . import config
from .data_manager import CSVDataManager
from .opcua_server import OPCUASimulator

_LOGGER = logging.getLogger(__name__)

_PACKAGE_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _PACKAGE_ROOT.parent


def create_app(
    data_manager: CSVDataManager,
    simulator: OPCUASimulator,
    *,
    secret_key: str | None = None,
) -> Flask:
    """Create and configure the Flask application."""

    app = Flask(
        __name__,
        template_folder=str(_PROJECT_ROOT / "templates"),
        static_folder=str(_PROJECT_ROOT / "static"),
    )
    app.config["SECRET_KEY"] = secret_key or config.DEFAULT_SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB uploads

    @app.route("/")
    def index() -> str:
        active_file = data_manager.active_file
        datasets = _build_dataset_metadata(data_manager, active_file)

        preview_columns: List[str] = []
        preview_rows: List[dict[str, object]] = []
        if active_file:
            try:
                df = data_manager.get_dataframe()
                preview_columns = list(df.columns)
                preview_rows = df.head(5).to_dict(orient="records")
            except Exception as exc:  # pragma: no cover - defensive logging
                _LOGGER.exception("Failed to build preview for %s", active_file)
                flash(f"Failed to load preview data: {exc}", "error")

        return render_template(
            "index.html",
            datasets=datasets,
            active_file=active_file,
            preview_columns=preview_columns,
            preview_rows=preview_rows,
        )

    @app.post("/upload")
    def upload_file() -> str:
        file = request.files.get("file")
        if not file:
            flash("Please choose a CSV file to upload.", "error")
            return redirect(url_for("index"))

        try:
            path = data_manager.save_upload(file)
        except ValueError as exc:
            flash(str(exc), "error")
        except Exception as exc:  # pragma: no cover - defensive logging
            _LOGGER.exception("Failed to save uploaded file")
            flash(f"Failed to save upload: {exc}", "error")
        else:
            flash(f"Uploaded {path.name} and set it as the active dataset.", "success")
            simulator.start()

        return redirect(url_for("index"))

    @app.post("/datasets/<path:filename>/activate")
    def activate_dataset(filename: str) -> str:
        try:
            path = data_manager.set_active_file(filename)
        except FileNotFoundError:
            flash(f"Dataset '{filename}' was not found.", "error")
        except Exception as exc:  # pragma: no cover - defensive logging
            _LOGGER.exception("Failed to activate dataset %s", filename)
            flash(f"Failed to activate dataset: {exc}", "error")
        else:
            flash(f"Active dataset set to {path.name}.", "success")
            simulator.start()

        return redirect(url_for("index"))

    return app


def _build_dataset_metadata(data_manager: CSVDataManager, active_file: Path | None) -> List[dict[str, object]]:
    datasets: List[dict[str, object]] = []
    for dataset in data_manager.list_datasets():
        try:
            stat = dataset.stat()
        except FileNotFoundError:
            continue

        datasets.append(
            {
                "name": dataset.name,
                "path": dataset,
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "size": stat.st_size,
                "is_active": active_file is not None and dataset.resolve() == active_file.resolve(),
            }
        )

    return datasets
