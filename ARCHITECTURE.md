============================================================
MEDLENS — ARCHITECTURE
============================================================

STACK
============================================================

Frontend:
- React
- Vite
- TypeScript
- Tailwind CSS
- shadcn/ui
- Lucide React

Backend:
- Python
- FastAPI
- Pydantic

Database:
- SQLite

Document Processing:
- PyMuPDF or pypdf

AI:
- AIProvider abstraction
- GroqProvider (initial implementation)
- Groq API
- Structured Outputs using JSON Schema

============================================================
FOLDER STRUCTURE
============================================================

medlens/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── types/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── range_engine.py
│   │   │   ├── conflict_engine.py
│   │   │   ├── provenance_service.py
│   │   │   ├── verification_service.py
│   │   │   └── safety_policy.py
│   │   ├── providers/
│   │   │   ├── ai_provider.py
│   │   │   └── groq_provider.py
│   │   └── main.py
│   ├── data/
│   │   ├── synthetic/
│   │   └── test/
│   └── requirements.txt
├── docs/
│   └── CONSTITUTION.md
└── ARCHITECTURE.md

============================================================
DATA FLOW
============================================================

COLLECT
→ User uploads medical document (PDF)
→ Document stored in SQLite
→ Document metadata recorded

EXTRACT
→ AIProvider receives document
→ Provider adapter (GroqProvider) calls AI model
→ AI extracts structured information
→ Raw extraction returned with metadata

STRUCTURE
→ Canonical schema applied
→ Pydantic models validate structure
→ Data transformed to canonical format

VALIDATE
→ RangeEngine checks reference ranges
→ ConflictEngine detects conflicts
→ ProvenanceService records source
→ VerificationService tracks state

TRACE
→ All facts linked to source document
→ Source page preserved where possible
→ Source text retained when available

FLAG
→ ConflictEngine flags inconsistencies
→ RangeEngine flags out-of-range values
→ SafetyPolicy validates against rules

HUMAN VERIFY
→ VerificationService manages lifecycle
→ States: AI_EXTRACTED → PENDING → EDITED → VERIFIED
→ Human edits preserve original AI extraction

EXPLAIN
→ AI summarizes verified information
→ AI explains terminology
→ AI answers questions about documented records

============================================================
PROVIDER BOUNDARY
============================================================

Architecture Layers:

Frontend
  ↓
FastAPI (Backend API)
  ↓
AIService (Domain Service)
  ↓
AIProvider (Interface)
  ↓
Provider Adapter (GroqProvider)
  ↓
AI Model (Groq API)

BOUNDARY RULES:

- Frontend MUST NOT import Groq
- Domain services MUST NOT import Groq
- Database MUST NOT depend on Groq
- Only GroqProvider may import Groq
- AIProvider defines the interface
- GroqProvider implements the interface

PORTABILITY:

Changing AI providers requires changes ONLY to:
- Provider Adapter (e.g., new OpenAIProvider)

NO changes required to:
- Frontend
- Database
- Canonical schema
- API contracts
- RangeEngine
- ConflictEngine
- ProvenanceService
- VerificationService
- SafetyPolicy

============================================================
SECURITY BOUNDARY
============================================================

API Keys:
- Stored in environment variables
- Never committed to repository
- Accessed only by Provider Adapter

Data Access:
- All API calls through FastAPI
- No direct database access from frontend
- SQLite file permissions restricted

Input Validation:
- Pydantic models validate all inputs
- File upload size limits
- File type validation

Output Safety:
- SafetyPolicy enforces immutable safety rules
- No diagnosis, prescribing, or recommendations
- Uncertain information marked as such
- Reference ranges from source only

============================================================
DOMAIN BOUNDARY
============================================================

DOMAIN SERVICES (Deterministic):

RangeEngine:
- Calculates reference-range status
- Outputs: WITHIN_SOURCE_RANGE, BELOW_SOURCE_RANGE, ABOVE_SOURCE_RANGE, NOT_DETERMINED
- Uses only source-provided ranges
- NEVER substitutes external ranges

ConflictEngine:
- Detects conflicts in extracted data
- Flags inconsistencies
- Does NOT silently resolve conflicts

ProvenanceService:
- Records source document
- Records source page when available
- Records source text when available
- Records origin, AI provider, AI model
- Records verification state and timestamp

VerificationService:
- Manages verification lifecycle
- States: AI_EXTRACTED → PENDING → EDITED → VERIFIED
- Preserves original AI extraction on edit
- Tracks human verification

SafetyPolicy:
- Enforces immutable safety rules
- Blocks diagnosis, prescribing, recommendations
- Ensures uncertain information is marked
- Validates against constitution

AI RESPONSIBILITIES:

AI MAY:
- Extract explicitly documented information
- Structure information
- Summarize verified information
- Explain terminology
- Answer questions about documented records

AI MAY NOT:
- Diagnose
- Prescribe
- Recommend treatment
- Recommend medication
- Recommend dosage changes
- Invent missing information
- Determine reference-range status
- Silently resolve conflicts

APPLICATION RESPONSIBILITIES:

Application code MUST own:
- Canonical schema
- Validation
- Reference-range calculation
- Conflict detection
- Provenance
- Verification state
- Audit history
- Safety policy
- Provider abstraction

============================================================
CANONICAL SCHEMA
============================================================

Core Entities:

Document:
- id
- filename
- upload_date
- file_path
- pages
- metadata

Fact:
- id
- document_id
- category (e.g., lab_result, medication, diagnosis)
- field_name
- value
- unit
- reference_range_low
- reference_range_high
- reference_range_status
- source_page
- source_text
- verification_state
- created_at
- updated_at

Provenance:
- id
- fact_id
- origin
- ai_provider
- ai_model
- timestamp

AuditLog:
- id
- fact_id
- action
- previous_value
- new_value
- actor (AI or human)
- timestamp

============================================================
IMMUTABLE SAFETY RULES
============================================================

MedLens MUST NOT:

1. Diagnose
2. Confirm a disease
3. Prescribe medication
4. Recommend medication
5. Recommend dosage changes
6. Recommend stopping medication
7. Recommend treatment
8. Invent medical values
9. Invent units
10. Invent dates
11. Invent reference ranges
12. Silently resolve conflicts
13. Present uncertain information as medical fact
14. Claim medical accuracy that has not been measured

============================================================
DONE
============================================================

ARCHITECTURE.md created.

Stack, folder structure, data flow, provider boundary,
security boundary, and domain boundary documented.

STOP.
