"""
AI Dispensing Defect Detective — Backend Entry Point

Run with:
    uvicorn main:app --reload --port 8000
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()


def get_cors_origins() -> list[str]:
    """
    Build allowed frontend origins for local dev and deployment.

    Set CORS_ORIGINS to a comma-separated list, for example:
    https://your-frontend.vercel.app,https://your-custom-domain.com
    """
    configured_origins = os.getenv("CORS_ORIGINS", "")
    origins = ["http://localhost:3000"]

    origins.extend(
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    )

    return origins

app = FastAPI(
    title="AI Dispensing Defect Detective",
    description="AI-powered troubleshooting engine for semiconductor dispensing defects",
    version="0.1.0",
)

# Allow local and deployed frontends to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Register API routers
# ------------------------------------------------------------------
from api.chat import router as chat_router
from api.diagnose import router as diagnose_router
from api.report import router as report_router
from api.knowledge import router as knowledge_router

app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(diagnose_router, prefix="/api", tags=["Diagnose"])
app.include_router(report_router, prefix="/api", tags=["Report"])
app.include_router(knowledge_router, prefix="/api", tags=["Knowledge"])


@app.get("/")
async def root():
    return {"status": "ok", "message": "AI Dispensing Defect Detective API is running"}
