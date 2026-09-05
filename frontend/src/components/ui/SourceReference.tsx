import { FileText, MapPin } from "lucide-react";
export function SourceReference({ document = "No source linked", page }: { document?: string; page?: number }) { return <div className="source-reference"><FileText size={15} /><span><b>Source linked</b><small>{document}{page ? ` · Page ${page}` : ""}</small></span></div>; }
