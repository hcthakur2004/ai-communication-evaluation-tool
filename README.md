# AI Communication Evaluation Tool (Rubric Scorer)

A lightweight, full‑stack tool to score free‑text transcripts against a rubric. The backend is built with FastAPI and a flexible rubric loader for Excel files; the frontend is a simple static UI. Scoring combines rubric keywords, semantic similarity (optional), and a soft length factor to produce per‑criterion scores and a weighted overall score.

## Features
- FastAPI backend with a single `/score` endpoint
- Excel rubric loader with flexible columns and automatic normalization
- Optional semantic scoring via `sentence-transformers/all-MiniLM-L6-v2`
- Soft length penalty to encourage within‑bounds responses (not harsh truncation)
- Simple, modern frontend to paste or upload transcript and view results

## Project Layout
- `backend/main.py`: FastAPI app, static frontend mount, model and rubric loading
- `backend/rubric_loader.py`: Excel parsing, column normalization, keyword cleaning, weight normalization
- `backend/scoring.py`: Scoring formula and feedback generation
- `frontend/`: Static UI (HTML/CSS/JS)
- `sample_inputs/Case study for interns.xlsx`: Example rubric

## Quick Start
1. Create and activate a virtual environment (Windows PowerShell):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```
4. Open the UI:
   - Visit `http://127.0.0.1:8000/`
   - Paste text or upload a `.txt` file, then click **Score**

## API
- Endpoint: `POST /score`
- Request JSON:
  ```json
  {
    "transcript": "string",
    "rubric_path": "optional string path to Excel",
    "use_semantic": true
  }
  ```
- Response JSON:
  ```json
  {
    "overall_score": 87.4,
    "words": 350,
    "criteria": [
      {
        "criterion": "Communication Clarity",
        "description": "Clear, concise answers with structure",
        "keywords": ["clear", "concise", "structure"],
        "weight": 0.15,
        "words": 350,
        "score": 90.5,
        "semantic_similarity": 0.72,
        "keyword_hits": ["clear", "structure"],
        "feedback": "Keywords found: clear, structure; Semantic similarity: 0.72; Within suggested length."
      }
    ]
  }
  ```

## Rubric Excel Format
Rubrics are loaded from Excel (first sheet). Column names are flexible; these aliases are recognized and normalized:
- `criterion`: [criterion, criteria, name, title]
- `description`: [description, desc, detail, rubric_description]
- `keywords`: [keywords, keys, phrases, terms]
- `weight`: [weight, score_weight, importance, priority]
- `min_words`: [min_words, minword, min, minlength]
- `max_words`: [max_words, maxword, max, maxlength]

Notes:
- If `criterion` is missing, it is derived from `description` or auto‑generated.
- If `description` is missing, it uses `criterion`.
- If `weight` is missing, equal weights are applied; weights are normalized to sum to 1 (`norm_weight`).
- A derived column `keywords_list` holds cleaned, comma‑separated keywords.

## Scoring Formula
Per criterion, the score blends three signals:
1. Keyword presence (`kw_score` in [0,1]): fraction of rubric keywords found in the transcript.
2. Semantic similarity (`sem_score` in [0,1]): cosine similarity between transcript and criterion description using `all-MiniLM-L6-v2` (clamped to non‑negative). If semantic model isn’t available or description is empty, this is 0.
3. Length factor (`length_factor` in [0.6,1.0]): soft penalty if the transcript is below `min_words` or above `max_words`. Feedback indicates whether you’re below/above bounds or within suggested length.

Signal blending:
- If a criterion has keywords: `base = 0.6*kw_score + 0.4*sem_score`
- If no keywords: `base = 0.3*kw_score + 0.7*sem_score`
- Per‑criterion: `score_pct = clamp(base, 0..1) * length_factor * 100`

Overall score:
- Weighted average of per‑criterion `score_pct` using `norm_weight`
- `overall = sum(score_pct_i * norm_weight_i)`; rounded to 2 decimals

Feedback:
- Includes keyword hits (or prompts to include key terms), semantic similarity value, and length advice.

## Semantic Model
- On startup, the backend attempts to load `sentence-transformers/all-MiniLM-L6-v2`.
- If unavailable, the app continues with `use_semantic=false` (or set `use_semantic` to false on the request) and semantic similarity defaults to 0.

## Troubleshooting
- Empty UI results: ensure the textarea has content; validation toasts appear for invalid input.
- `422 Unprocessable Entity`: check JSON body fields; the frontend sends `{ transcript, use_semantic, rubric_path? }`.
- Rubric path errors: provide a valid Excel path via the textbox or API `rubric_path`.
- Large model download: the semantic model may take time on first run.

## Development Scripts
- Restart dev server:
  ```powershell
  .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
  ```
- Sample API test (PowerShell):
  ```powershell
  $body = @{ transcript = 'This is a sample interview transcript about Python and data.'; use_semantic = $true } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/score' -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 4
  ```

## Deployment
- Any platform that can run `uvicorn` will work (Render, Railway, etc.).
- Serve the `frontend` directory statically; the backend already mounts it at `/`.
- For production, pin Python, FastAPI, and set `use_semantic` based on available compute.

## How to Run (Step-by-Step)
Follow these steps on Windows PowerShell to run the full project locally:

1. Create a virtual environment:
   ```powershell
   python -m venv .venv
   ```
2. Activate the environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
3. Install requirements:
   ```powershell
   pip install -r requirements.txt
   ```
4. Start the backend server (serves frontend too):
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```
5. Open the web UI:
   - Visit `http://127.0.0.1:8000/`
   - Paste or upload a `.txt` transcript and click **Score**

Optional settings:
- To use a custom rubric Excel, provide its path in the UI textbox or send `rubric_path` in the API request.
- Toggle semantic scoring via the UI checkbox or set `use_semantic` in the API payload.