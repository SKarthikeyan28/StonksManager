from fastapi import FastAPI

app = FastAPI(title="StonksManager Data Service")


@app.get("/health")
def health():
    """Simple health check so Docker/monitoring can verify the service is alive."""
    return {"status": "ok", "service": "data-service"}
