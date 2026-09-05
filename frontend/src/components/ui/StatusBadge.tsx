import { ArrowDown, ArrowUp, Check, CircleHelp, TriangleAlert } from "lucide-react";

const states = { within: [Check, "Within source range", "status-success"], below: [ArrowDown, "Below source range", "status-info"], above: [ArrowUp, "Above source range", "status-warning"], undetermined: [CircleHelp, "Not determined", "status-muted"], conflict: [TriangleAlert, "Conflict detected", "status-danger"] } as const;
export type StatusKind = keyof typeof states;
export function StatusBadge({ kind = "undetermined" }: { kind?: StatusKind }) { const [Icon, label, tone] = states[kind]; return <span className={`status-badge ${tone}`}><Icon size={14} aria-hidden="true" />{label}</span>; }
