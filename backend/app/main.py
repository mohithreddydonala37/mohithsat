from fastapi import FastAPI
from app.api import (
    verification_router,
    evidence_router,
    conflicts_router,
    patient_reports_router,
)
from app.models.database import init_db

app = FastAPI(
    title="MedLens API",
    description="AI-Powered Clinical Information Intelligence",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    init_db()
    print("Database initialized successfully.")


# Include routers
app.include_router(verification_router)
app.include_router(evidence_router)
app.include_router(conflicts_router)
app.include_router(patient_reports_router)


@app.get("/")
async def root():
    return {
        "message": "MedLens API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "verification": "operational",
            "evidence": "operational",
            "conflicts": "operational"
        }
    }
