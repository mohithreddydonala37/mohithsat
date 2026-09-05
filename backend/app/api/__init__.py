from .verification import router as verification_router
from .evidence import router as evidence_router
from .conflicts import router as conflicts_router
from .patient_reports import router as patient_reports_router

__all__ = [
    "verification_router",
    "evidence_router",
    "conflicts_router",
    "patient_reports_router",
]
