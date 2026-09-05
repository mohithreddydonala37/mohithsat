import type { ApiClient, Patient, PatientCreate, Report, ReviewResponse } from "../types/api";

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
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
};
