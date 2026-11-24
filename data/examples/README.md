# Example outputs

The requested reference video is https://www.youtube.com/watch?v=yGgq0sB9HeA.
On 2026-11-25, `yt-dlp --skip-download --list-subs` returned
“Sign in to confirm you're not a bot.” No transcript or analysis of that video
was available.

`synthetic.json` is a deterministic example using a short, invented test input
and a stubbed model response. It is **not** about the reference video. Reproduce
and validate it without YouTube or Ollama using:

```bash
pytest tests/test_pipeline.py::test_synthetic_example
```

Do not commit videos, audio, real raw full transcripts, or credentials.
