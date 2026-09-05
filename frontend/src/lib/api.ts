import type { ApiClient, Patient, PatientCreate, Report, ReviewResponse, VerificationResponse, Conflict } from "../types/api";

const baseUrl = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? "/api" : "http://localhost:8000");
async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`);
  if (!response.ok) throw new Error("The MedLens API is unavailable.");
  return response.json() as Promise<T>;
}
async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!response.ok) throw new Error(response.status >= 500 ? "The MedLens service is temporarily unavailable." : "Please review the information and try again.");
  return response.json() as Promise<T>;
}
async function upload<T>(path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${baseUrl}${path}`, { method: "POST", body });
  if (!response.ok) throw new Error(response.status >= 500 ? "The MedLens service is temporarily unavailable." : "That file could not be processed. Please choose another PDF.");
  return response.json() as Promise<T>;
}
export const apiClient: ApiClient = {
  getPatient: (id: number) => get<Patient>(`/patients/${id}`),
  getReport: (id: number) => get<Report>(`/reports/${id}`),
  createPatient: (patient: PatientCreate) => post<Patient>("/patients", patient),
  uploadReport: (patientId: number, file: File) => upload<import("../types/api").ReportUpload>(`/patients/${patientId}/reports`, file),
  extractReport: (reportId: number) => post<{ processing_status: string }>(`/reports/${reportId}/extract`, {}),
  getReview: (reportId: number) => get<ReviewResponse>(`/reports/${reportId}/review`),
  getAudit: (entityType: string, entityId: number) => get<{ audit_events: import("../types/api").AuditEvent[] }>(`/verification/audit/${entityType}/${entityId}`),
  editFact: (entityType: string, entityId: number, correctedValue: string) => post<VerificationResponse>(`/verification/edit/${entityType}/${entityId}`, { corrected_value: correctedValue }),
  verifyFact: (entityType: string, entityId: number) => post<VerificationResponse>(`/verification/verify/${entityType}/${entityId}`, {}),
  flagFact: (entityType: string, entityId: number, notes?: string) => post<VerificationResponse>(`/verification/flag/${entityType}/${entityId}`, { notes }),
  getConflicts: () => get<Conflict[]>("/conflicts"),
  resolveConflict: (id, decision, notes) => post<Conflict>(`/conflicts/${id}/resolve`, { decision, notes }),
  flagConflict: (id, notes) => post<Conflict>(`/conflicts/${id}/flag`, { notes }),
};
