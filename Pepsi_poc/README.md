# PepsiCo POC — FastAPI on Azure

A FastAPI application deployed on Azure using Container Registry and Container Instances.

## Local Development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for Swagger UI.

## Azure Deployment

Built and deployed via Azure Container Registry and Azure Container Instances.
