# ADIF Analyzer — QRP-Stat

Web application for analyzing ADIF files (Amateur Data Interchange Format) with contact visualization on an interactive map.

Analysis results are oriented toward the [Club 72](http://club-72.ru/#qrp) activity tables.

## Features

### ADIF File Analysis

- Statistics by countries (WKD countries), fields (WKD fields), and squares (WKD squares)
- Power categories:
  - **ALL** — all contacts
  - **QRP** — up to 5W
  - **QRPp** — up to 1W
  - **QRP-X** — up to 0.1W (100mW)
  - **QRPu** — up to 0.01W (10mW)
- Text power values: `QRP` → 5W, `QRPp` → 1W, `QRP-X` → 0.1W, `QRPu` → 0.01W
- Band statistics (160M–2M, 70CM) with ODX (longest contact)
- Top-20 most frequent callsigns
- Locator and country lookup via QRZ.com (pyhamtools)
- Correct prefix handling (e.g., LA/KK6IK → QTH for Norway)
- Distance calculation via Maidenhead locators (pyhamtools + Haversine fallback)

### Contact Map

- Interactive map using **Leaflet.js** with **CartoDB Spotify Dark** tiles
- Color differentiation by power category:
  - ALL — blue
  - QRP — green
  - QRPp — orange
  - QRP-X — red
  - QRPu — purple
- Radio buttons for category switching
- Contact lines from operator to each contact
- Auto-zoom on load and category switch
- Yellow marker for operator position
- Popups: callsign, band, power, distance
- Canvas renderer for performance

### Large File Optimization

- Files **<10,000 QSO**: each QSO as individual marker, lines up to 2,000 points
- Files **≥10,000 QSO**: deduplication by locator coordinates, popup shows QSO count, marker size proportional (log scale, 7–16px)

### Analysis Progress

- Displays "Processed X of Y QSO" in real time
- Update interval: 1 second

### Interface

- Two-column layout: form on the left, results on the right
- Results stretch to full height of right panel
- Fluid page, responsive design (<768px: single column)
- "Analyze" button disabled until file is loaded
- "Download TXT" button disabled until analysis completes
- "Hide contact map" checkbox to skip map data collection
- Multilingual: RU/EN interface, RU/EN statistics

## Running

```bash
pip install -r requirements.txt
python3 app.py
```

Server available at http://localhost:5000

### CLI Mode

```bash
python3 main_analysis.py <file.adif> [locator]
python3 main_analysis.py <folder>/ [locator]
```

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main page |
| POST | `/analyze` | Upload files and start analysis |
| GET | `/status/<job_id>` | Task status and result |
| GET | `/download/<job_id>` | Download TXT |
| GET | `/map/<job_id>` | Map data (JSON) |

## Technologies

- **Backend**: Python 3, Flask, adif_io, pyhamtools
- **Frontend**: Vanilla JS, Leaflet.js, CartoDB Spotify Dark tiles
- **Deployment**: Render.com (gunicorn)

## Dependencies

```
flask==3.1.3
adif_io==0.6.1
pyhamtools==0.12.0
requests==2.33.1
gunicorn==23.0.0
```

## Structure

```
├── app.py              # Flask server (API + request handling)
├── main_analysis.py    # ADIF file analysis engine
├── templates/
│   └── index.html      # Frontend (HTML + CSS + JS)
├── uploads/            # Temporary files (results)
├── requirements.txt    # Dependencies
├── render.yaml         # Deployment config
└── Procfile            # Gunicorn config
```

## Authors

Original code: **Andrey UB3BBB (R4NCU)**
Enhanced with AI assistance (Manus & DeepSeek)
Contact: andrey.R4NCU@gmail.com
Repository: https://github.com/r4ncu/adif-analyzer

License: AS IS
