"""Maintenance fund report web app with Ollama chat and dynamic plots."""

import os
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from data_loader import (
    build_summary,
    context_for_ai,
    export_cleaned_csv,
    export_cleaned_json,
    export_data_filename,
    get_dataset,
    load_default,
)
from file_parser import parse_upload
from md_preview import (
    PREVIEW_CSS,
    list_reports,
    render_live_report_html,
    render_markdown_html,
    render_report,
    save_uploaded_report,
    wrap_export_html,
)
from ollama_client import (
    DEFAULT_OLLAMA_BASE_URL,
    chat,
    extract_plot_spec,
    extract_report_updates,
    health_check,
    normalize_ollama_url,
    strip_plot_block,
)
from plot_engine import generate_plot
from session_store import create_session, session_info

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

app = FastAPI(title="Maintenance Fund Report", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup():
    load_default()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    model: str | None = None
    generate_plot: bool = True
    report_summary: str = ""


class PlotRequest(BaseModel):
    spec: dict[str, Any]


class ExportRequest(BaseModel):
    title: str = "Maintenance Fund Report"
    summary_markdown: str = ""
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    source_file: str = ""
    period: str = ""


class RenderMarkdownRequest(BaseModel):
    markdown: str = ""
    title: str = "Preview"


class PreviewLiveRequest(BaseModel):
    title: str = "Maintenance Fund Report"
    summary_markdown: str = ""
    blocks: list[dict[str, Any]] = Field(default_factory=list)
    source_file: str = ""
    period: str = ""


def _session_id(x_session_id: str | None = None) -> str | None:
    if x_session_id and x_session_id != "default":
        return x_session_id
    return None


def _ollama_url(x_ollama_url: str | None = Header(None, alias="X-Ollama-Url")) -> str | None:
    if not x_ollama_url or not x_ollama_url.strip():
        return None
    try:
        return normalize_ollama_url(x_ollama_url)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@app.get("/api/ollama/config")
async def api_ollama_config():
    return {"default_url": DEFAULT_OLLAMA_BASE_URL}


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
async def api_health(
    x_session_id: str | None = Header(None),
    x_ollama_url: str | None = Header(None, alias="X-Ollama-Url"),
):
    ollama_url = None
    if x_ollama_url and x_ollama_url.strip():
        try:
            ollama_url = normalize_ollama_url(x_ollama_url)
        except ValueError as e:
            ollama = {"ok": False, "url": x_ollama_url.strip(), "error": str(e)}
        else:
            ollama = await health_check(ollama_url)
    else:
        ollama = await health_check()
    data_ok = (APP_DIR.parent / "X.md").exists()
    sess = session_info(_session_id(x_session_id))
    return {
        "data_file": data_ok,
        "ollama": ollama,
        "session": sess,
        "default_ollama_url": DEFAULT_OLLAMA_BASE_URL,
    }


@app.get("/api/session")
async def api_session(x_session_id: str | None = Header(None)):
    return session_info(_session_id(x_session_id))


@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename")
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 20 MB)")
    try:
        dataset = parse_upload(file.filename, data)
    except Exception as e:
        raise HTTPException(400, str(e)) from e
    if file.filename.lower().endswith(".md"):
        save_uploaded_report(file.filename, data)
    sid = create_session(dataset, source="upload")
    summary = build_summary(dataset)
    return {
        "session_id": sid,
        "filename": file.filename,
        "months": dataset["months_parsed"],
        "date_range": dataset["date_range"],
        "summary": summary,
    }


@app.get("/api/data")
async def api_data(refresh: bool = False, x_session_id: str | None = Header(None)):
    try:
        return get_dataset(refresh=refresh, session_id=_session_id(x_session_id))
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@app.get("/api/export/data")
async def api_export_data(
    format: Literal["json", "csv"] = Query("json"),
    x_session_id: str | None = Header(None),
):
    try:
        data = get_dataset(session_id=_session_id(x_session_id))
    except Exception as e:
        raise HTTPException(500, str(e)) from e

    if format == "csv":
        content = export_cleaned_csv(data)
        media_type = "text/csv; charset=utf-8"
    else:
        content = export_cleaned_json(data)
        media_type = "application/json; charset=utf-8"

    filename = export_data_filename(data, format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/summary")
async def api_summary(refresh: bool = False, x_session_id: str | None = Header(None)):
    try:
        data = get_dataset(refresh=refresh, session_id=_session_id(x_session_id))
        return build_summary(data)
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@app.get("/api/models")
async def api_models(ollama_url: str | None = Depends(_ollama_url)):
    h = await health_check(ollama_url)
    if not h.get("ok"):
        raise HTTPException(503, f"Ollama unavailable: {h.get('error')}")
    return {"models": h.get("models", []), "url": h.get("url")}


@app.get("/api/reports")
async def api_reports_list():
    return {"reports": list_reports(), "preview_css": PREVIEW_CSS}


@app.get("/api/reports/preview")
async def api_report_preview(report_id: str = Query(..., description="Relative path, e.g. x_analysis/MAINTENANCE_FUND_REPORT.md")):
    try:
        return render_report(report_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@app.post("/api/reports/render-markdown")
async def api_render_markdown(req: RenderMarkdownRequest):
    try:
        html = render_markdown_html(req.markdown, title=req.title)
        return {"html": html, "title": req.title}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/reports/preview-live")
async def api_preview_live(req: PreviewLiveRequest):
    try:
        html = render_live_report_html(
            req.title,
            req.summary_markdown,
            req.blocks,
            source_file=req.source_file,
            period=req.period,
        )
        return {"html": html, "title": req.title}
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/plot")
async def api_plot(req: PlotRequest, x_session_id: str | None = Header(None)):
    try:
        data = get_dataset(session_id=_session_id(x_session_id))
        return generate_plot(req.spec, data)
    except Exception as e:
        raise HTTPException(400, str(e)) from e


@app.post("/api/chat")
async def api_chat(
    req: ChatRequest,
    x_session_id: str | None = Header(None),
    ollama_url: str | None = Depends(_ollama_url),
):
    try:
        data = get_dataset(session_id=_session_id(x_session_id))
        system = context_for_ai(data, req.report_summary)
        messages = [{"role": "system", "content": system}]
        messages += [{"role": m.role, "content": m.content} for m in req.messages]

        result = await chat(messages, model=req.model, base_url=ollama_url)
        content = result.get("message", {}).get("content", "")

        plot_result = None
        if req.generate_plot:
            spec = extract_plot_spec(content)
            if spec:
                try:
                    plot_result = generate_plot(spec, data)
                except Exception as e:
                    content += f"\n\n*(Plot generation failed: {e})*"

        report_updates = extract_report_updates(content)

        return {
            "reply": strip_plot_block(content),
            "plot": plot_result,
            "report_updates": report_updates,
            "model": result.get("model"),
        }
    except httpx.HTTPError as e:
        raise HTTPException(503, f"Ollama error: {e}") from e
    except Exception as e:
        if "Connect" in str(e) or "connection" in str(e).lower():
            url = ollama_url or DEFAULT_OLLAMA_BASE_URL
            raise HTTPException(
                503,
                f"Cannot reach Ollama at {url}. Check the URL in settings and ensure Ollama is running.",
            ) from e
        raise HTTPException(500, str(e)) from e


@app.post("/api/export/html")
async def api_export_html(req: ExportRequest):
    body = render_live_report_html(
        req.title,
        req.summary_markdown,
        req.blocks,
        source_file=req.source_file,
        period=req.period,
    )
    return HTMLResponse(wrap_export_html(req.title, body))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8765"))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
