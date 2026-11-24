# YouTube Analyser Agent

An open-source, transcript-first YouTube analysis agent. It turns a YouTube URL into:

- a concise summary and key claims;
- evidence-backed examples, quotes, and calls to action;
- a timestamped narrative breakdown using `hook`, `promise`, `stakes`, `open_loop`, `proof`, `re_hook`, `mini_payoff`, `payoff`, and `cta`;
- Markdown and JSON suitable for research or reusable script templates.

The project intentionally reuses mature open-source building blocks instead of reimplementing them:

- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) for metadata and audio fallback;
- `yt-dlp` for caption-first retrieval, including automatic captions;
- [Invidious](https://github.com/iv-org/invidious) as an optional caption/metadata fallback;
- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) for local transcription fallback;
- [Ollama](https://ollama.com/) for local structured analysis;
- FastAPI and Pydantic for the API contract.

## WSL + Anaconda setup

Install WSL, Anaconda or Miniconda in the Linux distribution, and
[Ollama](https://ollama.com/download/linux). Run these commands from the repository
root in WSL. The environment is isolated; ffmpeg is installed by Conda.

```bash
conda env create -f environment.yml
conda activate youtube-analyser
ollama pull llama3.1:8b
```

Start `ollama serve` in another WSL terminal if the Ollama service is not already
running. Whisper runs on CPU and downloads its model on first use. Both YouTube
and model downloads need network access.

### YouTube bot-verification mitigation

The recommended first-line fix is the maintained
[bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider)
plugin. It generates proof-of-origin tokens for yt-dlp. Install it in the same
Conda environment as this project, then run its local provider (Docker is the
simplest WSL setup):

```bash
conda activate youtube-analyser
pip install -e ".[youtube-bot]"
docker run --name bgutil-provider -d --init \
  -p 127.0.0.1:4416:4416 brainicism/bgutil-ytdlp-pot-provider
```

The repository also includes an equivalent `docker-compose.yml`; run
`docker compose up -d bgutil-provider` from the project root.

The provider is optional and cannot guarantee bypassing every YouTube block.
Do not expose port `4416` beyond localhost. For authenticated browser traffic,
set `YTDLP_COOKIES_FROM_BROWSER=chrome` or `YTDLP_COOKIES_FILE=/path/cookies.txt`;
never commit cookie files. You can also set `YTDLP_PO_TOKEN` and
`YTDLP_PO_TOKEN_CONTEXT` when you have a per-video token.

If yt-dlp still fails, the agent tries Invidious. Configure one or more trusted
instances explicitly, or allow discovery:

```bash
export INVIDIOUS_INSTANCE_URLS="https://your-invidious.example"
export INVIDIOUS_DISCOVERY=true
```

Ollama cannot repair a blocked network request: it only analyzes text after a
transcript is obtained. The retrieval layer therefore fails over before Ollama
is called.

## CLI

```bash
youtube-analyser analyze \
  "https://www.youtube.com/watch?v=yGgq0sB9HeA" \
  --output-dir data/examples \
  --language zh \
  --model llama3.1:8b
```

The command first uses available captions in the requested language. If none are
available, it downloads temporary audio and transcribes it with faster-whisper.
Temporary files are removed after the request. Inputs longer than 24,000
transcript characters are rejected rather than silently truncated.

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

The API returns a validated `AnalysisResult` JSON object. Set `OLLAMA_HOST` when Ollama is not running on its default local endpoint. The API has no authentication; bind it only to localhost and do not expose it to untrusted networks.

## Development

```bash
pytest
ruff check .
```

No videos, audio files, raw full transcripts, or credentials belong in this repository. Example outputs should contain only derived analysis and short evidence snippets.

## Project status

The first reference video is `yGgq0sB9HeA`. YouTube returned a bot-verification
error during retrieval, so no claims about that video's content are provided.
See [the reproducible synthetic example](data/examples/README.md). Model output
is interpretive and may contain errors; verify quotes and timestamps against
the video before reuse.

The product and chapter-oriented experience were inspired by
[DevRico003/youtube_summarizer](https://github.com/DevRico003/youtube_summarizer);
this Python implementation does not copy its code.
