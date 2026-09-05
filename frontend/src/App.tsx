import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { PlaceholderPage } from "./pages/PlaceholderPage";
import { LandingPage } from "./pages/LandingPage";
import { PatientIntakePage } from "./pages/PatientIntakePage";
import { ReportUploadPage } from "./pages/ReportUploadPage";
import { ExtractionReviewPage } from "./pages/ExtractionReviewPage";
import { ConflictCenterPage } from "./pages/ConflictCenterPage";
export default function App() { return <Routes><Route path="/" element={<LandingPage />} /><Route element={<AppShell />}><Route path="/overview" element={<PlaceholderPage title="Overview" description="A clear view of what is documented, linked to evidence, and still awaiting human verification." />} /><Route path="/reports" element={<PlaceholderPage title="Reports" description="Review source documents and their processing state." />} /><Route path="/timeline" element={<PlaceholderPage title="Timeline" description="Follow documented changes across the patient record." />} /><Route path="/conflicts" element={<ConflictCenterPage />} /><Route path="/evidence" element={<PlaceholderPage title="Evidence" description="Connect every structured fact back to its source document." />} /><Route path="/patients/new" element={<PatientIntakePage />} /><Route path="/patients/:patientId/reports/new" element={<ReportUploadPage />} /><Route path="/reports/:reportId/review" element={<ExtractionReviewPage />} /><Route path="*" element={<Navigate to="/" replace />} /></Route></Routes>; }
