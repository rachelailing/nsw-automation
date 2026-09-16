"""
AI Dispensing Defect Detective — Backend Entry Point

Run with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="AI Dispensing Defect Detective",
    description="AI-powered troubleshooting engine for semiconductor dispensing defects",
    version="0.1.0",
)

# Allow frontend (Next.js on port 3000) to call the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# Register API routers
# ------------------------------------------------------------------
from api.chat import router as chat_router
from api.diagnose import router as diagnose_router
from api.upload_image import router as upload_image_router
from api.report import router as report_router

app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(diagnose_router, prefix="/api", tags=["Diagnose"])
app.include_router(upload_image_router, prefix="/api", tags=["Image Upload"])
app.include_router(report_router, prefix="/api", tags=["Report"])


@app.get("/")
async def root():
    return {"status": "ok", "message": "AI Dispensing Defect Detective API is running"}
