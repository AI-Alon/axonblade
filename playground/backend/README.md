# AxonBlade Playground Backend

FastAPI backend that runs AxonBlade code in a subprocess and streams output via SSE.

## Deploy to Render (free tier)

1. Go to [render.com](https://render.com) and create a new **Web Service**
2. Connect your `AI-Alon/axonblade` GitHub repo
3. Configure:
   - **Root Directory:** *(leave blank — Render uses the repo root)*
   - **Build Command:** `pip install -r playground/backend/requirements.txt`
   - **Start Command:** `uvicorn playground.backend.main:app --host 0.0.0.0 --port $PORT`
   - **Python version:** 3.11
4. Click **Deploy**
5. Copy your service URL (e.g. `https://axonblade-playground.onrender.com`)
6. Update `BACKEND_URL` in `docs/playground.html` to match

## Run locally

```bash
pip install fastapi uvicorn[standard] pydantic requests
uvicorn playground.backend.main:app --reload
```

The API will be at `http://localhost:8000`.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/run` | Run AxonBlade code, stream output via SSE |
| `GET` | `/health` | Health check |

### POST /run

**Request:**
```json
{ "code": "write(\"Hello!\")" }
```

**Response:** `text/event-stream`
```
data: Hello!

data: [DONE]
```

## Restrictions

- 5-second execution timeout
- `io` and `http` modules are blocked
