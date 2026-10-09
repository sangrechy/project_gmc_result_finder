# FastResults - Unofficial TNMGRMU Result Viewer

> [!IMPORTANT]
> **Legal Disclaimer**: FastResults is an independent, **unofficial** educational utility developed for students to look up publicly accessible exam results. This project is **NOT affiliated with, authorized, maintained, sponsored, or endorsed by The Tamil Nadu Dr. M.G.R. Medical University (TNMGRMU)**. All official inquiries, mark sheets, and certifications must be accessed through the official university portal at [www.tnmgrmu.ac.in](https://www.tnmgrmu.ac.in).

An ultra-clean, high-performance Python backend and modern **Neumorphism (Soft UI)** web platform for querying TNMGRMU Exam Results.

---

## Features

- **Live University Results**: Directly queries examination endpoints with zero mock fallbacks.
- **IPv4 Connection Optimization**: Enforces IPv4 socket resolution (`14.139.177.26`), preventing NAT64 IPv6 connection timeouts.
- **Real-Time Streaming Batch**: Real-time progress bar formatted as `X% (Y out of Z data collected)` via Server-Sent Events (SSE).
- **Export Options**: Download batch results directly in `.csv` or formatted `.xlsx` (Excel) workbooks.
- **Two-Tier Cache Engine**: L1 Memory LRU + L2 SQLite database (`data/results_cache.db`) for instant repeat lookups.
- **Tactile Neumorphic UI**: Soft UI dual-shadow interface with responsive Light and Dark themes.

---

## Directory Structure

```
project_gmc_result_finder/
├── app/
│   ├── api/
│   │   ├── endpoints.py      # Isolated URL constants & builders
│   │   ├── network.py        # Socket patcher for IPv4 connectivity
│   │   ├── caller.py         # Standalone API request functions
│   │   └── parsers.py        # Response parsers
│   ├── cache.py              # Two-tier cache engine (Memory + SQLite)
│   ├── client.py             # Multi-step orchestrator client
│   ├── config.py             # Server & network configuration
│   ├── models.py             # Pydantic schemas
│   └── routes.py             # FastAPI REST endpoints & SSE stream
├── static/
│   ├── app.js                # Frontend logic & SSE stream reader
│   ├── index.html            # Neumorphic dashboard template
│   ├── style.css             # Soft UI stylesheet
│   └── header.png            # Logo & favicon
├── data/                     # Local SQLite cache storage
├── main.py                   # FastAPI server & CLI utility
├── requirements.txt          # Dependencies
├── run.bat                   # Windows launch script
├── ai.readme                 # AI & developer architectural reference
└── README.md
```

---

## Quick Start

### 1. Launch Web Server
Double-click `run.bat` or execute:
```powershell
python main.py serve
```
- Web Application: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- API Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. CLI Commands
```powershell
# Query a single registration number
python main.py get <REGISTRATION_NUMBER>

# Force fresh lookup bypassing local cache
python main.py get <REGISTRATION_NUMBER> --refresh

# Batch query a roll number range
python main.py batch <START_ROLL> <END_ROLL> --csv results.csv

# Clear local cache
python main.py clear-cache
```

---

## Technical Documentation
For AI and developer reference without inline comments, see [ai.readme](ai.readme).
