import os
from typing import Optional
from fastapi import FastAPI, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .rubric_loader import load_rubric
from .scoring import score_transcript

app = FastAPI(title="Rubric Scoring Service")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_RUBRIC_PATH = os.path.join(BASE_DIR, "sample_inputs", "Case study for interns.xlsx")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Global caches
RUBRIC_DF = None
EMBED_MODEL = None


class ScoreRequest(BaseModel):
    transcript: str
    rubric_path: Optional[str] = None
    use_semantic: bool = True


@app.on_event("startup")
async def startup_event():
    global RUBRIC_DF, EMBED_MODEL
    # Load rubric
    try:
        rubric_path = DEFAULT_RUBRIC_PATH
        RUBRIC_DF = load_rubric(rubric_path)
        print(f"Loaded rubric from: {rubric_path} ({len(RUBRIC_DF)} rows)")
    except Exception as e:
        print(f"Failed to load rubric: {e}")
        RUBRIC_DF = None

    # Load sentence transformer model if available
    try:
        from sentence_transformers import SentenceTransformer
        EMBED_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        print("Embedding model loaded: all-MiniLM-L6-v2")
    except Exception as e:
        print(f"Semantic model unavailable: {e}")
        EMBED_MODEL = None


@app.post("/score")
async def score_endpoint(payload: ScoreRequest):
    # Load rubric per request if provided
    rubric_df = RUBRIC_DF
    if payload.rubric_path:
        rubric_df = load_rubric(payload.rubric_path)

    if rubric_df is None:
        return {"error": "Rubric is not loaded. Please provide a valid Excel path."}

    model = EMBED_MODEL if payload.use_semantic else None
    result = score_transcript(payload.transcript, rubric_df, model=model)
    return result


# Serve frontend static files
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


# Fallback root if frontend not found
@app.get("/", response_class=HTMLResponse)
async def root_fallback():
    if os.path.isdir(FRONTEND_DIR):
        # StaticFiles will handle
        with open(os.path.join(FRONTEND_DIR, "index.html"), "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Rubric Scoring Service</h1><p>POST to /score with a transcript.</p>")