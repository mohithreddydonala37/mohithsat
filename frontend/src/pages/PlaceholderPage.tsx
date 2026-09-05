import { FileSearch } from "lucide-react";
import { PageHeader } from "../components/PageHeader";
export function PlaceholderPage({ title, description }: { title: string; description: string }) { return <div className="page"><PageHeader title={title} description={description} /><section className="empty-state" role="status"><span className="empty-icon"><FileSearch size={22} /></span><h2>Foundation ready</h2><p>This workspace will connect to documented records in the next phase.</p><span className="status-badge status-muted">Not available yet</span></section></div>; }
