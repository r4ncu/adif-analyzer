# ADIF Analyzer

Web application for analyzing amateur radio ADIF logs and generating statistics by countries, locators, and power.

**Link:** [ADIF Analyzer](https://adif-analyzer.onrender.com)

## Purpose

The program is designed to analyze ADIF files (standard radio communication log format) and output detailed statistics. Results are oriented toward the [Club 72](http://club-72.ru/#qrp) activity tables — a community of low-power (QRP) amateur radio operators.

## Requirements

1. **ADIF file (.adi)** — a radio contact log exported from ANYLOG, UR5EQF_log, N1MM, Log4OM, MacLogger DX, or any other logging software.
2. **Callsign** — your callsign (e.g., R4NCU).
3. **Locator** — your Maidenhead locator, 4–6 characters (e.g., LO48VI). Entered manually.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| Callsign | Required | Your callsign |
| Locator | Required | Your Maidenhead locator (4 or 6 characters) |
| ADIF file(s) | Required | One or more .adi files |
| Power for all QSOs | Optional | Checkbox + input field. When enabled, the specified power is applied to **all** QSOs in the log instead of the TX_PWR field value |

## Results

### Overall statistics for all QSOs
Number of worked countries (WKD countries), fields (WKD fields), and squares (WKD squares) across **all** QSOs regardless of power.

### Statistics by power category

| Category | Maximum power |
|----------|---------------|
| QRP | up to 5 W |
| QRPp | up to 1 W |
| QRP-X | up to 0.1 W (100 mW) |
| QRPu | up to 0.01 W (10 mW) |

For each category:
- Number of QSOs
- Countries, fields, and squares (WKD)
- Longest contact (ODX) with distance and power

### Additional
- Top-20 most frequent callsigns
- Band statistics (160M–2M) with ODX
- Total unique callsigns
- Average QSOs per callsign

## Language

The interface and results are available in **Russian** and **English**. Switch using flag buttons 🇷🇺 / 🇬🇧. The selection persists between sessions.

## Technical Details

- **Backend:** Python + Flask + `adif_io` (ADIF parsing) + `pyhamtools` (callsign lookup from cqdx database)
- **Frontend:** HTML/CSS/JS with async polling
- **Deployment:** GitHub → Render.com, auto-deploy on push to `main`
- **Limitations:** Analysis of 44,000 QSOs takes ~30 seconds. Background processing with status polling every 2 seconds.

## Usage from Command Line

```bash
python main_analysis.py log.adi LO48VI
python main_analysis.py /path/to/folder/ LO48VI
```

## Authors

Original code — Andrey UB3BBB. Enhancement — AI + human.
