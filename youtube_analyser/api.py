from fastapi import FastAPI, HTTPException

from .models import AnalysisResult, AnalyzeRequest
from .service import run_analysis

app = FastAPI(title="YouTube Analyser Agent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalysisResult)
def analyze_video(request: AnalyzeRequest) -> AnalysisResult:
    try:
        return run_analysis(
            request.url,
            language=request.language,
            model=request.model,
            whisper_model=request.whisper_model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
