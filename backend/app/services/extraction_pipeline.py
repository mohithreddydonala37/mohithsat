import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.database import (
    AllergyDB, ConditionDB, ConflictDB, LabResultDB, MedicationDB,
    ProvenanceDB, ReportDB, VerificationDB,
)
from app.models.enums import Origin, VerificationStatus
from app.models import Allergy, Condition, LabResult, Medication
from app.config import get_settings
from app.providers.groq_provider import GroqProvider
from app.providers.mock_provider import MockAIProvider
from app.services.ai_service import AIService
from app.services.conflict_engine import ConflictEngine
from app.services.provenance_service import ProvenanceService


def _pages(report: ReportDB) -> list[dict[str, Any]]:
    try:
        metadata = json.loads(report.report_metadata or "{}")
        pages = metadata.get("pages", [])
        return pages if isinstance(pages, list) else []
    except json.JSONDecodeError:
        return []


def _provider():
    if get_settings().ai_provider.lower() == "mock":
        return MockAIProvider()
    return GroqProvider()


async def extract_report(report: ReportDB, db: Session) -> dict[str, Any]:
    page_records = _pages(report)
    if not page_records:
        raise ValueError("Report has no readable page text")
    document_text = "\n\n".join(
        f"[Page {page.get('page_number')}]\n{page.get('page_text', '')}"
        for page in page_records
    )
    result = await AIService(_provider()).extract_from_document(
        document_text, report.id, report.filename
    )
    if not result["success"]:
        raise ValueError("Extraction could not be completed")
    data = result["data"]
    provider = result["provider"]
    model = result["model"]

    lab_models = data["lab_results"]
    medication_models = data["medications"]
    allergy_models = data["allergies"]
    condition_models = data["conditions"]
    db_labs: list[LabResultDB] = []
    db_meds: list[MedicationDB] = []
    db_allergies: list[AllergyDB] = []
    db_conditions: list[ConditionDB] = []
    for lab in lab_models:
        row = LabResultDB(**{key: value for key, value in lab.model_dump().items() if key not in {"id", "report_id", "created_at", "origin", "verification_status", "provider", "model"}}, report_id=report.id, origin=Origin.AI_EXTRACTED.value, verification_status=VerificationStatus.PENDING.value, provider=provider, model=model)
        db.add(row); db_labs.append(row)
    for med in medication_models:
        row = MedicationDB(**{key: value for key, value in med.model_dump().items() if key not in {"id", "report_id", "created_at", "origin", "verification_status", "provider", "model"}}, report_id=report.id, origin=Origin.AI_EXTRACTED.value, verification_status=VerificationStatus.PENDING.value, provider=provider, model=model)
        db.add(row); db_meds.append(row)
    for allergy in allergy_models:
        row = AllergyDB(**{key: value for key, value in allergy.model_dump().items() if key not in {"id", "report_id", "created_at", "origin", "verification_status", "provider", "model"}}, report_id=report.id, origin=Origin.AI_EXTRACTED.value, verification_status=VerificationStatus.PENDING.value, provider=provider, model=model)
        db.add(row); db_allergies.append(row)
    for condition in condition_models:
        row = ConditionDB(**{key: value for key, value in condition.model_dump().items() if key not in {"id", "report_id", "created_at", "origin", "verification_status", "provider", "model"}}, report_id=report.id, origin=Origin.AI_EXTRACTED.value, verification_status=VerificationStatus.PENDING.value, provider=provider, model=model)
        db.add(row); db_conditions.append(row)
    db.flush()

    domain_labs = [LabResult.model_validate({**lab.model_dump(), "id": row.id, "report_id": report.id}) for lab, row in zip(lab_models, db_labs)]
    domain_meds = [Medication.model_validate({**med.model_dump(), "id": row.id, "report_id": report.id}) for med, row in zip(medication_models, db_meds)]
    domain_allergies = [Allergy.model_validate({**item.model_dump(), "id": row.id, "report_id": report.id}) for item, row in zip(allergy_models, db_allergies)]
    domain_conditions = [Condition.model_validate({**item.model_dump(), "id": row.id, "report_id": report.id}) for item, row in zip(condition_models, db_conditions)]
    conflicts = ConflictEngine.detect_all_conflicts(domain_labs, domain_meds, domain_allergies, domain_conditions)
    for conflict in conflicts:
        db.add(ConflictDB(**conflict.model_dump(exclude={"id", "created_at"})))
    for entity_type, models in (("lab_result", zip(domain_labs, db_labs)), ("medication", zip(domain_meds, db_meds)), ("allergy", zip(domain_allergies, db_allergies)), ("condition", zip(domain_conditions, db_conditions))):
        for item, row in models:
            db.add(ProvenanceDB(**ProvenanceService.record_ai_extraction(entity_type, row.id, report.filename, item.source_page, item.source_text, provider, model).model_dump(exclude={"id"})))
            db.add(VerificationDB(entity_type=entity_type, entity_id=row.id, status=VerificationStatus.PENDING.value, original_ai_value=json.dumps(item.model_dump(mode="json")), created_at=datetime.now(timezone.utc)))
    metadata = _metadata(report)
    metadata["processing_status"] = "READY_FOR_REVIEW"
    report.report_metadata = json.dumps(metadata)
    db.commit()
    return {"provider": provider, "model": model, "conflicts": len(conflicts), "processing_status": metadata["processing_status"]}


def _metadata(report: ReportDB) -> dict[str, Any]:
    try:
        value = json.loads(report.report_metadata or "{}")
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}
