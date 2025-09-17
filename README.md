# OPC UA CSV Simulator

This project exposes values from CSV files through an OPC UA server and
provides a small web UI to manage datasets. It is designed for quickly
mocking data sources when testing OPC UA clients locally or inside Docker
Desktop.

## Features

- Upload CSV files via the built-in web interface and activate them without
  restarting the container.
- Automatically maps CSV columns to OPC UA variables following a clean
  namespace layout (`Objects → Machines → <Machine Name>`).
- Streams rows at a configurable interval and restarts the cycle after a
  configurable pause.
- Provides a preview of the active dataset directly in the UI.
- Ships with a sample dataset for quick smoke testing.

## Project layout

```
opcua_sim/
├── config.py          # Configuration defaults sourced from env vars
├── data_manager.py    # Handles CSV storage and uploads
├── main.py            # Application entrypoint
├── opcua_server.py    # OPC UA server implementation
└── web.py             # Flask application factory
```

Static assets live in `static/` and HTML templates in `templates/`.

## Getting started locally

1. Install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Launch the simulator:

   ```bash
   python -m opcua_sim.main
   ```

3. Open <http://localhost:8000> to upload CSV files and monitor the active
   dataset. The OPC UA endpoint is available at
   `opc.tcp://localhost:4840/`.

Stop the process with `Ctrl+C`. The simulator shuts down the OPC UA server
cleanly.

## Running in Docker Desktop

Build and run the container:

```bash
docker build -t opcua-sim .
docker run --rm -p 4840:4840 -p 8000:8000 opcua-sim
```

Navigate to <http://localhost:8000> to access the UI. Uploaded CSV files are
stored inside the container under `/app/data`.

### Persisting datasets between runs

Mount a local directory to `/app/data`:

```bash
docker run --rm -p 4840:4840 -p 8000:8000 \
  -v $(pwd)/data:/app/data opcua-sim
```

## Configuration

Environment variables control runtime behaviour:

| Variable | Description | Default |
| -------- | ----------- | ------- |
| `DATA_DIR` | Directory where CSV files are stored. | `data` |
| `DEFAULT_CSV_FILE` | CSV file activated on startup (relative to `DATA_DIR`). | `sample-machine-data.csv` |
| `OPCUA_ENDPOINT` | OPC UA endpoint URL. | `opc.tcp://0.0.0.0:4840/` |
| `OPCUA_NAMESPACE_URI` | Namespace URI registered with the server. | `http://example.org/opcua-sim` |
| `OPCUA_MACHINE_NAME` | Browse name for the machine object. | `MachineA` |
| `ROW_UPDATE_INTERVAL` | Delay in seconds between rows. | `1.0` |
| `CYCLE_DELAY` | Delay in seconds after processing all rows. | `10.0` |
| `TIME_COLUMN` | Column name ignored when creating OPC UA variables. | `siteTime` |
| `WEB_HOST` | Host interface for the web UI. | `0.0.0.0` |
| `WEB_PORT` | Port for the web UI. | `8000` |
| `LOG_LEVEL` | Python logging level. | `INFO` |
| `FLASK_SECRET_KEY` | Secret key for session handling. | `opcua-sim-secret` |

## Upload workflow

1. Open the UI and upload a CSV file.
2. The file is stored under `DATA_DIR` with a timestamped name and activated
   immediately.
3. The OPC UA server refreshes its variables to match the new CSV columns and
   begins streaming rows from the uploaded dataset.
4. Previously uploaded files remain available and can be re-activated from the
   dataset table.

## CSV requirements

- Files must have a header row with unique column names.
- The column specified by `TIME_COLUMN` (defaults to `siteTime`) is ignored in
  OPC UA publishing.
- Missing values are automatically filled with `0.0`.

## Development tips

- The project uses standard Python logging; set `LOG_LEVEL=DEBUG` to see
  detailed output.
- Update the HTML template in `templates/index.html` or the stylesheet in
  `static/styles.css` to tweak the UI.
- Add new sample datasets to the `data/` folder.

## License

This repository is provided as-is without warranty. Adapt it to your testing
environment as needed.
