from fastapi import FastAPI
from app.routes import items
from app.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PepsiCo POC API",
    description="FastAPI application deployed on Azure",
    version="1.0.0"
)

app.include_router(items.router, prefix="/api/v1", tags=["items"])

@app.get("/")
def root():
    return {
        "status": "healthy",
        "message": "PepsiCo POC API is running on Azure",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
