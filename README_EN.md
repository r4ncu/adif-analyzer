# ADIF Analyzer

Web application for analyzing ADIF files (Amateur Data Interchange Format) with contact visualization on an interactive map.

https://adif-analyzer.onrender.com

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
- Band statistics (160M–2M, 70CM) with ODX (longest contact)
- Top-20 most frequent callsigns
- Locator and country lookup via QRZ.com (pyhamtools)
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

## Authors

Original code: **Andrey UB3BBB**
Contact: andrey.R4NCU@gmail.com

License: AS IS

cu on air 73 es 72
