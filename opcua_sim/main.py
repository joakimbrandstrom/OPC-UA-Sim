"""Application entrypoint for the OPC UA simulator."""

from __future__ import annotations

import logging
import signal
import threading
from contextlib import suppress

from waitress import create_server

from . import config
from .data_manager import CSVDataManager
from .opcua_server import OPCUASimulator
from .web import create_app


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, config.DEFAULT_LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_simulator() -> tuple[CSVDataManager, OPCUASimulator]:
    data_manager = CSVDataManager()
    simulator = OPCUASimulator(
        data_manager,
        endpoint=config.DEFAULT_OPCUA_ENDPOINT,
        namespace_uri=config.DEFAULT_NAMESPACE_URI,
        machine_name=config.DEFAULT_MACHINE_NAME,
        update_interval=config.DEFAULT_UPDATE_INTERVAL,
        cycle_delay=config.DEFAULT_CYCLE_DELAY,
    )
    return data_manager, simulator


def main() -> None:
    configure_logging()
    data_manager, simulator = build_simulator()
    simulator.start()

    app = create_app(data_manager, simulator, secret_key=config.DEFAULT_SECRET_KEY)
    logging.getLogger(__name__).info(
        "Starting web UI on %s:%s", config.DEFAULT_WEB_HOST, config.DEFAULT_WEB_PORT
    )

    server = create_server(app, host=config.DEFAULT_WEB_HOST, port=config.DEFAULT_WEB_PORT)
    shutdown_event = threading.Event()

    def _shutdown_handler(signum, frame):  # pragma: no cover - signal handler
        if shutdown_event.is_set():
            return
        logging.getLogger(__name__).info("Received signal %s. Shutting down.", signum)
        shutdown_event.set()
        with suppress(Exception):
            server.close()
        simulator.stop()

    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)

    try:
        server.run()
    finally:
        with suppress(Exception):
            server.close()
            simulator.stop()


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()
