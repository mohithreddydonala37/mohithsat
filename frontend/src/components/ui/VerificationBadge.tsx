import { CheckCircle2, Clock3, Flag, Pencil } from "lucide-react";
export type VerificationState = "pending" | "verified" | "edited" | "flagged";
const config = { pending: [Clock3, "Pending verification"], verified: [CheckCircle2, "Verified"], edited: [Pencil, "Edited"], flagged: [Flag, "Flagged"] } as const;
export function VerificationBadge({ state = "pending" }: { state?: VerificationState }) { const [Icon, label] = config[state]; return <span className={`verification-badge verification-${state}`}><Icon size={14} aria-hidden="true" />{label}</span>; }
