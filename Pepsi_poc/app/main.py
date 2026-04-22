from fastapi import FastAPI
from app.routes import items
from app.routes import agent
from app.database import Base, engine
from app.config import settings
import logging
import os

Base.metadata.create_all(bind=engine)

# Setup Application Insights
if settings.ENVIRONMENT == "production":
    try:
        from opencensus.ext.azure.log_exporter import AzureLogHandler
        from opencensus.ext.azure.trace_exporter import AzureExporter
        from opencensus.trace.samplers import ProbabilitySampler
        from opencensus.ext.fastapi.fastapi_middleware import FastAPIMiddleware

        conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
        if conn_str:
            logger = logging.getLogger(__name__)
            logger.addHandler(AzureLogHandler(connection_string=conn_str))
            logger.setLevel(logging.INFO)
            logger.info("Application Insights connected!")
        else:
            print("WARNING: APPLICATIONINSIGHTS_CONNECTION_STRING not set")

    except Exception as e:
        print(f"App Insights setup failed: {e}")

app = FastAPI(
    title="PepsiCo POC API",
    description="FastAPI application deployed on Azure with Agent Diagnostics",
    version="1.0.0"
)

# Setup App Insights middleware after app creation
if settings.ENVIRONMENT == "production":
    try:
        conn_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
        if conn_str:
            from opencensus.ext.azure.trace_exporter import AzureExporter
            from opencensus.trace.samplers import ProbabilitySampler
            from opencensus.ext.fastapi.fastapi_middleware import FastAPIMiddleware
            app.add_middleware(
                FastAPIMiddleware,
                exporter=AzureExporter(connection_string=conn_str),
                sampler=ProbabilitySampler(1.0)
            )
    except Exception as e:
        print(f"App Insights middleware failed: {e}")

# Routers
app.include_router(items.router, prefix="/api/v1", tags=["items"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])


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
