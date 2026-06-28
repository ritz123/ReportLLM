# Residential Society Maintenance Fund

Tools to parse, clean, analyze, and report on a residential society maintenance ledger (8 units, Bangalore). The project turns messy monthly expense sheets into structured data, charts, written reports, and an interactive web app with local AI assistance.

## Quick start

**Web app** (recommended):

```bash
./start_report_app.sh
```

Open [http://localhost:8765](http://localhost:8765).

**Batch analysis** (charts + JSON + markdown report):

```bash
python analyze_x.py
python generate_pdf.py   # optional PDF from the markdown report
```

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (used by `start_report_app.sh`) or `pip`
- [Ollama](https://ollama.com/) for the AI chat features (optional for viewing data and exports)
- A local ledger file **`X.md`** or **`X.xlsx`** in the project root (not stored in git — see below)

```bash
ollama pull llama3.2
ollama serve
```

## Local data (not in git)

Ledger files and generated outputs stay on your machine only:

| Path | Purpose |
|------|---------|
| `X.md` / `X.xlsx` | Source expense ledger (place here after clone) |
| `x_analysis/` | Charts, `analysis.json`, and report outputs from `analyze_x.py` |
| `maintenance_app/reports/` | Uploaded `.md` reports from the web app |

Clone the repo, add your own `X.md` or `X.xlsx`, then run `./start_report_app.sh` or `python analyze_x.py`.

## Project layout

```
├── X.md / X.xlsx          # Your ledger (local only — not in git)
├── analyze_x.py           # Parse ledger → charts + analysis.json
├── generate_pdf.py        # Build PDF from the markdown report
├── start_report_app.sh    # Launch the web app
├── x_analysis/            # Generated locally (gitignored)
└── maintenance_app/       # FastAPI web UI (see maintenance_app/README.md)
```

## Data cleaning

Parsing lives in `analyze_x.py`. Each month sheet is normalized to:

- **Expense** — left-column line items and `Total` (treated as authoritative)
- **Bank balance** — closing bank balance when present (authoritative)
- **Collections / income** — right-column resident `Total` when reliable; otherwise inferred as:

  `income = closing_balance − opening_balance + expense`

Category labels (Electricity, Water, Security, etc.) come from keyword rules tuned for this society’s vendors and descriptions. Upload `.xlsx`, `.xls`, or `.md` files through the web app to parse other ledgers in the same shape.

## Web app features

| Feature | Description |
|---------|-------------|
| **Generate Summary** | Key metrics, top categories, observations |
| **Upload Sheet** | `.xlsx`, `.xls`, or `.md` with monthly tabs/sections |
| **Open .md file** | Preview static reports (`X.md`, `MAINTENANCE_FUND_REPORT.md`, …) |
| **AI Assistant** | Ollama chat — analysis, plots, report updates |
| **Preview / Export Report** | HTML document with summary + AI-added sections and charts |
| **Export Data** | Download cleaned dataset as **JSON** or **CSV** |

Use **Auto-add charts & report updates** in chat to apply AI changes and charts to the live report automatically.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Default model |
| `PORT` | `8765` | Web server port |

## API (web app)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Data + Ollama status |
| GET | `/api/summary` | Auto-generated summary |
| GET | `/api/data` | Full parsed dataset |
| GET | `/api/export/data?format=json\|csv` | Download cleaned data |
| GET | `/api/reports/preview?report_id=…` | Render a markdown file |
| POST | `/api/upload` | Upload expense sheet |
| POST | `/api/chat` | AI chat (plots + report updates) |
| POST | `/api/export/html` | Export live report as HTML |

## Example prompts

- "Summarize the fund's financial health and add key points to the report"
- "Plot income vs expense by quarter"
- "Show a pie chart of expense categories for 2024"
- "Line chart of electricity bills over time"

## Manual setup (without start script)

```bash
cd maintenance_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

More detail on the web app: [maintenance_app/README.md](maintenance_app/README.md).
