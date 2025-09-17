"""Configuration helpers for the OPC UA simulator."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

DEFAULT_DATA_DIR: Final[Path] = Path(os.getenv("DATA_DIR", "data"))
DEFAULT_SAMPLE_FILE: Final[str] = os.getenv("DEFAULT_CSV_FILE", "sample-machine-data.csv")
DEFAULT_OPCUA_ENDPOINT: Final[str] = os.getenv("OPCUA_ENDPOINT", "opc.tcp://0.0.0.0:4840/")
DEFAULT_NAMESPACE_URI: Final[str] = os.getenv("OPCUA_NAMESPACE_URI", "http://example.org/opcua-sim")
DEFAULT_MACHINE_NAME: Final[str] = os.getenv("OPCUA_MACHINE_NAME", "MachineA")
DEFAULT_UPDATE_INTERVAL: Final[float] = float(os.getenv("ROW_UPDATE_INTERVAL", "1.0"))
DEFAULT_CYCLE_DELAY: Final[float] = float(os.getenv("CYCLE_DELAY", "10.0"))
DEFAULT_TIME_COLUMN: Final[str] = os.getenv("TIME_COLUMN", "siteTime")
DEFAULT_WEB_HOST: Final[str] = os.getenv("WEB_HOST", "0.0.0.0")
DEFAULT_WEB_PORT: Final[int] = int(os.getenv("WEB_PORT", "8000"))
DEFAULT_LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")
DEFAULT_SECRET_KEY: Final[str] = os.getenv("FLASK_SECRET_KEY", "opcua-sim-secret")
