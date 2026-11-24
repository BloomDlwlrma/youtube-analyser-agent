# YouTube Analyser Agent

An open-source, transcript-first YouTube analysis agent. It turns a YouTube URL into:

- a concise summary and key claims;
- evidence-backed examples, quotes, and calls to action;
- a timestamped narrative breakdown using `hook`, `promise`, `stakes`, `open_loop`, `proof`, `re_hook`, `mini_payoff`, `payoff`, and `cta`;
- Markdown and JSON suitable for research or reusable script templates.

The project intentionally reuses mature open-source building blocks instead of reimplementing them:

- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) for metadata and audio fallback;
- [`youtube-transcript-api`](https://github.com/jdepoix/youtube-transcript-api) for caption-first retrieval;
- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) for local transcription fallback;
- [Ollama](https://ollama.com/) for local structured analysis;
- FastAPI and Pydantic for the API contract.

## WSL + Anaconda setup

```bash
conda env create -f environment.yml
conda activate youtube-analyser
ollama pull llama3.1:8b
```

For NVIDIA GPU transcription, install the CUDA-compatible `ctranslate2`/PyTorch stack for your driver. CPU mode works without CUDA.

## CLI

```bash
youtube-analyser analyze \
  "https://www.youtube.com/watch?v=yGgq0sB9HeA" \
  --output-dir data/examples \
  --language zh \
  --model llama3.1:8b
```

The command first uses available captions. If captions are unavailable, it downloads temporary audio and transcribes it with faster-whisper. Audio and raw transcript caches are ignored by Git.

## API

```bash
uvicorn youtube_analyser.api:app --reload
```

Then `POST /analyze`:

```json
{
  "url": "https://www.youtube.com/watch?v=yGgq0sB9HeA",
  "language": "zh",
  "model": "llama3.1:8b"
}
```

The API returns a validated `AnalysisResult` JSON object. Set `OLLAMA_HOST` when Ollama is not running on its default local endpoint.

## Development

```bash
pytest
ruff check .
```

No videos, audio files, raw full transcripts, or credentials belong in this repository. Example outputs should contain only derived analysis and short evidence snippets.

## Project status

The first reference video is `yGgq0sB9HeA`. A generated example is committed only when the transcript can be retrieved reproducibly; otherwise the CLI reports the source failure rather than fabricating a transcript.
