FROM python:3.11-slim

# ─────────────────────────────────────────────
# System deps: ODBC driver for Azure SQL + Node.js for frontend build
# ─────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc-dev \
    apt-transport-https \
    ca-certificates && \
    # Microsoft ODBC 18 for Azure SQL Server
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | \
    gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > \
    /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 && \
    # Node.js 20 LTS (for React/JSX dashboard build)
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ─────────────────────────────────────────────
# Python dependencies
# ─────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────
# Frontend (React/JSX dashboard) build
# Place your dashboard source in a `dashboard/` folder at project root
# Output goes to app/static/ and is served by FastAPI as static files
# ─────────────────────────────────────────────
COPY dashboard/package*.json ./dashboard/
RUN npm install --prefix ./dashboard

COPY dashboard/ ./dashboard/
RUN npm run build --prefix ./dashboard && \
    mkdir -p app/static && \
    cp -r dashboard/dist/* app/static/

# ─────────────────────────────────────────────
# Application source
# ─────────────────────────────────────────────
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
