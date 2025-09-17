"""OPC UA server that publishes values from CSV files."""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Dict, Optional

import pandas as pd
from opcua import Server, ua

from .data_manager import CSVDataManager

_LOGGER = logging.getLogger(__name__)


class OPCUASimulator:
    """Continuously publish CSV data through an OPC UA server."""

    def __init__(
        self,
        data_manager: CSVDataManager,
        *,
        endpoint: str,
        namespace_uri: str,
        machine_name: str,
        update_interval: float,
        cycle_delay: float,
    ) -> None:
        self.data_manager = data_manager
        self.endpoint = endpoint
        self.namespace_uri = namespace_uri
        self.machine_name = machine_name
        self.update_interval = update_interval
        self.cycle_delay = cycle_delay

        self._server: Optional[Server] = None
        self._namespace_index: Optional[int] = None
        self._machine_node = None
        self._nodes: Dict[str, ua.Node] = {}
        self._known_columns: set[str] = set()
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._node_lock = threading.RLock()
        self._state_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def start(self) -> None:
        with self._state_lock:
            if self._thread and self._thread.is_alive():
                _LOGGER.debug("OPC UA simulator already running")
                return

            self._setup_server()
            self._running.set()
            self._thread = threading.Thread(target=self._run, name="opcua-simulator", daemon=True)
            self._thread.start()
            _LOGGER.info("OPC UA simulator started at %s", self.endpoint)

    def stop(self) -> None:
        with self._state_lock:
            self._running.clear()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
            self._thread = None

            if self._server:
                _LOGGER.info("Stopping OPC UA server")
                try:
                    self._server.stop()
                finally:
                    self._server = None
                    self._namespace_index = None
                    self._machine_node = None
                    self._nodes.clear()
                    self._known_columns.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _setup_server(self) -> None:
        server = Server()
        server.set_endpoint(self.endpoint)
        namespace_index = server.register_namespace(self.namespace_uri)

        machines_folder = server.nodes.objects.add_folder(namespace_index, "Machines")
        machine_node = machines_folder.add_object(namespace_index, self.machine_name)

        self._server = server
        self._namespace_index = namespace_index
        self._machine_node = machine_node

        server.start()

    def _ensure_nodes(self, df: pd.DataFrame) -> None:
        columns = list(self.data_manager.iter_value_columns(df))
        if set(columns) == self._known_columns:
            return

        _LOGGER.info("Refreshing OPC UA nodes to match CSV columns")
        with self._node_lock:
            for node in self._nodes.values():
                try:
                    node.delete()
                except Exception:  # pragma: no cover - best effort cleanup
                    _LOGGER.exception("Failed to delete OPC UA node")
            self._nodes.clear()

            self._known_columns = set(columns)
            first_row = df.iloc[0] if not df.empty else None
            for column in columns:
                initial_value = self._coerce_numeric(first_row[column]) if first_row is not None else 0.0
                node = self._machine_node.add_variable(
                    self._make_node_id(column),
                    column.strip(),
                    initial_value,
                )
                node.set_writable()
                self._nodes[column] = node

    def _run(self) -> None:
        while self._running.is_set():
            try:
                df = self.data_manager.get_dataframe()
            except FileNotFoundError:
                _LOGGER.warning("Active CSV file not found. Waiting before retrying.")
                time.sleep(self.cycle_delay)
                continue
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.exception("Failed to load CSV data")
                time.sleep(self.cycle_delay)
                continue

            if self._server is None:
                _LOGGER.error("OPC UA server is not initialised")
                time.sleep(self.cycle_delay)
                continue

            self._ensure_nodes(df)
            records = df.to_dict(orient="records")
            if not records:
                _LOGGER.info("No rows found in CSV file. Sleeping for %s seconds", self.cycle_delay)
                time.sleep(self.cycle_delay)
                continue

            for record in records:
                if not self._running.is_set():
                    break
                self._update_nodes(record)
                time.sleep(self.update_interval)

            _LOGGER.debug("Completed a CSV replay cycle. Sleeping for %s seconds", self.cycle_delay)
            time.sleep(self.cycle_delay)

    def _update_nodes(self, record: dict[str, object]) -> None:
        with self._node_lock:
            for column, node in self._nodes.items():
                value = self._coerce_numeric(record.get(column))
                try:
                    node.set_value(value)
                except Exception:  # pragma: no cover - defensive logging
                    _LOGGER.exception("Failed to update node for column %s", column)

    def _make_node_id(self, column: str) -> ua.NodeId:
        if self._namespace_index is None:
            raise RuntimeError("Namespace has not been registered")
        digest = hashlib.sha1(column.strip().encode("utf-8")).hexdigest()[:12]
        return ua.NodeId(f"Tag_{digest}", self._namespace_index)

    @staticmethod
    def _coerce_numeric(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
