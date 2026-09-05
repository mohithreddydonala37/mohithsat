from typing import Dict, Any, Optional
from app.providers.ai_provider import AIProvider
from app.models import (
    LabResult,
    Medication,
    Allergy,
    Condition,
    Origin,
    VerificationStatus
)
from app.models.extraction import ExtractionPayload
from app.services.range_engine import RangeEngine
from app.services.provenance_service import ProvenanceService
from app.services.safety_policy import SafetyPolicy


class AIService:
    """
    AI service layer.
    
    Responsibilities:
    - Call AIProvider
    - Validate AI response
    - Map provider output to canonical MedLens schema
    - Handle provider failures
    - Preserve provenance
    - Never bypass deterministic validation
    """
    
    def __init__(self, provider: AIProvider):
        """
        Initialize AIService with an AI provider.
        
        Args:
            provider: AI provider implementation (e.g., GroqProvider)
        """
        self.provider = provider
    
    async def extract_from_document(
        self,
        document_text: str,
        report_id: int,
        source_document: str
    ) -> Dict[str, Any]:
        """
        Extract structured information from a document.
        
        Args:
            document_text: Text content from medical document
            report_id: ID of the report
            source_document: Name/path of source document
            
        Returns:
            Dictionary containing extracted entities and provenance
        """
        # Define extraction schema
        extraction_schema = {
            "lab_results": [
                {
                    "test_name": str,
                    "value": Optional[str],
                    "unit": Optional[str],
                    "reference_low": Optional[float],
                    "reference_high": Optional[float],
                    "reference_text": Optional[str],
                    "observation": Optional[str],
                    "report_date": Optional[str],
                    "source_page": Optional[int],
                    "source_text": Optional[str]
                }
            ],
            "medications": [
                {
                    "name": str,
                    "dosage": Optional[str],
                    "frequency": Optional[str],
                    "route": Optional[str],
                    "start_date": Optional[str],
                    "source_page": Optional[int],
                    "source_text": Optional[str]
                }
            ],
            "allergies": [
                {
                    "allergen": str,
                    "severity": Optional[str],
                    "reaction": Optional[str],
                    "source_page": Optional[int],
                    "source_text": Optional[str]
                }
            ],
            "conditions": [
                {
                    "name": str,
                    "diagnosis_date": Optional[str],
                    "status": Optional[str],
                    "notes": Optional[str],
                    "source_page": Optional[int],
                    "source_text": Optional[str]
                }
            ]
        }
        
        try:
            # Call provider for extraction
            extracted_data = await self.provider.extract(document_text, extraction_schema)
            extracted_data = ExtractionPayload.model_validate(extracted_data).model_dump()
            
            # Validate and map to canonical schema
            canonical_results = self._map_to_canonical_schema(
                extracted_data,
                report_id,
                source_document
            )
            
            # Apply deterministic validation
            validated_results = self._apply_deterministic_validation(canonical_results)
            
            return {
                "success": True,
                "data": validated_results,
                "provider": self.provider.get_provider_name(),
                "model": self.provider.get_model_name()
            }
            
        except Exception as e:
            # Handle provider failures gracefully
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider.get_provider_name(),
                "model": self.provider.get_model_name()
            }
    
    def _map_to_canonical_schema(
        self,
        extracted_data: Dict[str, Any],
        report_id: int,
        source_document: str
    ) -> Dict[str, Any]:
        """
        Map provider output to canonical MedLens schema.
        
        Args:
            extracted_data: Raw data from AI provider
            report_id: ID of the report
            source_document: Source document name
            
        Returns:
            Data in canonical MedLens schema format
        """
        canonical = {
            "lab_results": [],
            "medications": [],
            "allergies": [],
            "conditions": []
        }
        
        # Map lab results
        for lab in extracted_data.get("lab_results", []):
            lab_result = LabResult(
                report_id=report_id,
                test_name=lab.get("test_name", ""),
                value=lab.get("value"),
                unit=lab.get("unit"),
                reference_low=lab.get("reference_low"),
                reference_high=lab.get("reference_high"),
                reference_text=lab.get("reference_text"),
                observation=lab.get("observation"),
                report_date=lab.get("report_date"),
                source_page=lab.get("source_page"),
                source_text=lab.get("source_text"),
                origin=Origin.AI_EXTRACTED,
                verification_status=VerificationStatus.PENDING,
                provider=self.provider.get_provider_name(),
                model=self.provider.get_model_name()
            )
            canonical["lab_results"].append(lab_result)
        
        # Map medications
        for med in extracted_data.get("medications", []):
            medication = Medication(
                report_id=report_id,
                name=med.get("name", ""),
                dosage=med.get("dosage"),
                frequency=med.get("frequency"),
                route=med.get("route"),
                start_date=med.get("start_date"),
                end_date=med.get("end_date"),
                source_page=med.get("source_page"),
                source_text=med.get("source_text"),
                origin=Origin.AI_EXTRACTED,
                verification_status=VerificationStatus.PENDING,
                provider=self.provider.get_provider_name(),
                model=self.provider.get_model_name()
            )
            canonical["medications"].append(medication)
        
        # Map allergies
        for allergy_data in extracted_data.get("allergies", []):
            allergy = Allergy(
                report_id=report_id,
                allergen=allergy_data.get("allergen", ""),
                severity=allergy_data.get("severity"),
                reaction=allergy_data.get("reaction"),
                source_page=allergy_data.get("source_page"),
                source_text=allergy_data.get("source_text"),
                origin=Origin.AI_EXTRACTED,
                verification_status=VerificationStatus.PENDING,
                provider=self.provider.get_provider_name(),
                model=self.provider.get_model_name()
            )
            canonical["allergies"].append(allergy)
        
        # Map conditions
        for condition_data in extracted_data.get("conditions", []):
            condition = Condition(
                report_id=report_id,
                name=condition_data.get("name", ""),
                diagnosis_date=condition_data.get("diagnosis_date"),
                status=condition_data.get("status"),
                notes=condition_data.get("notes"),
                source_page=condition_data.get("source_page"),
                source_text=condition_data.get("source_text"),
                origin=Origin.AI_EXTRACTED,
                verification_status=VerificationStatus.PENDING,
                provider=self.provider.get_provider_name(),
                model=self.provider.get_model_name()
            )
            canonical["conditions"].append(condition)
        
        return canonical
    
    def _apply_deterministic_validation(
        self,
        canonical_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply deterministic validation (RangeEngine) to extracted data.
        
        Args:
            canonical_data: Data in canonical schema format
            
        Returns:
            Data with range classification applied
        """
        # Apply RangeEngine to lab results
        for lab_result in canonical_data.get("lab_results", []):
            range_status = RangeEngine.classify_range(
                value=lab_result.value,
                reference_low=lab_result.reference_low,
                reference_high=lab_result.reference_high
            )
            lab_result.range_status = range_status
        
        return canonical_data
    
    async def summarize_records(
        self,
        verified_data: Dict[str, Any]
    ) -> str:
        """
        Generate summary from verified structured data.
        
        Args:
            verified_data: Verified structured medical information
            
        Returns:
            Factual, source-grounded summary
        """
        try:
            summary = await self.provider.summarize(verified_data)
            return summary
        except Exception as e:
            # Handle provider failures
            return f"Summary generation failed: {str(e)}"
    
    async def answer_question(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Answer a question about documented records.
        
        Args:
            question: User question
            context: Relevant medical record context
            
        Returns:
            Factual answer based on documented information
        """
        if SafetyPolicy.is_restricted(question):
            return SafetyPolicy.safe_response()

        try:
            answer = await self.provider.answer(question, context)
            return answer
        except Exception as e:
            # Handle provider failures
            return f"Failed to answer question: {str(e)}"
