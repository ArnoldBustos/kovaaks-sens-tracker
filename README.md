# Corporate Serf Tracker

Desktop app for analyzing KovaaK's Sensitivity Method runs. Inspired by the Corporate Serf method.

## Features

- Load a KovaaK stats folder and group plays by scenario
- Compare best score, median, total plays, estimated best cm/360, and estimated worst cm/360
- Recommend the next cm/360 to test based on current data gaps
- Track the best-performing crosshair and crosshair scale from the highest scoring run
- Manually tag runs with cm/360 values when the CSV does not include them
- Filter by cm/360 range and hide specific cm values per scenario

## Project structure

```text
corporate-serf-tracker/
  corporate_serf_tracker/
    __init__.py
    analysis.py
    app.py
    constants.py
    formatting.py
    parsing.py
    storage.py
  main.py
  requirements.txt
```

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
