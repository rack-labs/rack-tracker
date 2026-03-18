# poseLandmarker_Python

`uv` based FastAPI backend skeleton for video upload, pose inference, analysis, and feedback generation.

## Run

```bash
uv sync
uv run main.py
```

## Endpoints

- `GET /`
- `POST /jobs`
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/result`
