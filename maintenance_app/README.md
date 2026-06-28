# Maintenance Fund Report Web App

Interactive web UI to load the society maintenance ledger, view an auto-generated summary, chat with a local AI (Ollama), and build custom reports with dynamically generated charts.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) running locally with at least one model pulled, e.g.:

```bash
ollama pull llama3.2
ollama serve
```

- Data file `X.md` in the parent directory (`/userworkqum/bisarkar/misc/X.md`)

## Setup

```bash
cd maintenance_app
pip install -r requirements.txt
```

## Run

```bash
cd maintenance_app
python app.py
```

Open **http://localhost:8765** in your browser.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Default model if none selected |
| `PORT` | `8765` | Web server port |

Example:

```bash
OLLAMA_BASE_URL=http://localhost:11434 OLLAMA_MODEL=llama3.2 python app.py
```

## Features

- **MD Preview** — dropdown to render and display any project `.md` report (`X.md`, `x_analysis/MAINTENANCE_FUND_REPORT.md`, uploaded `.md` files)
- **Upload expense sheet** — `.xlsx`, `.xls`, or `.md` (one sheet per month, e.g. `Jan 2022`)
- **Generate Summary** — loads parsed data and shows key metrics, categories, and observations
- **Resizable layout** — drag the divider between Report and AI chat panels
- **AI Chat** — ask natural-language questions; Ollama answers using full fund context
- **Dynamic Plots** — request charts in chat; AI returns a plot spec and the server renders it
- **Report updates** — AI can add sections/observations to the report; auto-applied or via "Add to Report"
- **Export Report** — download the current report (summary + added blocks) as HTML

## Example chat prompts

- "Summarize the fund's financial health"
- "Plot income vs expense by quarter"
- "Show a pie chart of expense categories for 2024"
- "Line chart of electricity bills over time"
- "What were the highest expense months and why?"

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Data file + Ollama status |
| GET | `/api/reports` | List available `.md` reports |
| GET | `/api/reports/preview?report_id=…` | Render markdown report as HTML |
| GET | `/api/session` | Active session info |
| POST | `/api/upload` | Upload `.xlsx` / `.md` expense sheet (multipart `file`) |
| GET | `/api/summary` | Auto-generated summary |
| GET | `/api/data?refresh=true` | Full parsed dataset |
| GET | `/api/models` | List Ollama models |
| POST | `/api/chat` | Chat with AI (may include plot) |
| POST | `/api/plot` | Generate plot from JSON spec |
| POST | `/api/export/html` | Export report as HTML |
