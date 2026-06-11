import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, FileText, MessageSquareText } from "lucide-react";
import { committeesService } from "@/api/committees";

interface CompletedSectionProps {
  committeeId: string;
  completionNotes?: string | null;
}

export function CompletedSection({ committeeId, completionNotes }: CompletedSectionProps) {
  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["committee-docs", committeeId],
    queryFn: () => committeesService.getDocuments(committeeId),
    enabled: !!committeeId,
  });

  return (
    <div className="rounded-lg border border-emerald-200 bg-white overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-3 bg-emerald-600 px-6 py-4">
        <CheckCircle2 className="h-5 w-5 text-white shrink-0" />
        <div>
          <h3 className="text-base font-semibold text-white">Completed</h3>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Remarks */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <MessageSquareText className="h-4 w-4 text-emerald-600" />
            <span className="text-sm font-semibold text-slate-800">Completion Remarks</span>
          </div>
          {completionNotes ? (
            <div className="bg-slate-50 rounded-lg border border-slate-100 px-4 py-3 relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500" />
              <p className="text-sm text-slate-700 leading-relaxed font-serif italic">
                &ldquo;{completionNotes}&rdquo;
              </p>
            </div>
          ) : (
            <p className="text-sm text-slate-400 italic">No remarks were added.</p>
          )}
        </div>

        {/* Documents */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-emerald-600" />
            <span className="text-sm font-semibold text-slate-800">Documents</span>
            {!isLoading && (
              <span className="text-xs text-slate-400">
                ({docs.length} file{docs.length !== 1 ? "s" : ""})
              </span>
            )}
          </div>

          {isLoading ? (
            <p className="text-sm text-slate-400 py-3 text-center">Loading documents…</p>
          ) : docs.length === 0 ? (
            <p className="text-sm text-slate-400 italic">No documents were uploaded.</p>
          ) : (
            <div className="space-y-2">
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3"
                >
                  <FileText className="h-4 w-4 text-emerald-600 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{doc.name}</p>
                    {doc.uploaded_by && (
                      <p className="text-[11px] text-slate-400">{doc.uploaded_by}</p>
                    )}
                  </div>
                  <button
                    onClick={() => committeesService.viewDocument(committeeId, doc.id)}
                    className="text-xs font-semibold text-emerald-600 hover:underline shrink-0"
                  >
                    View
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default CompletedSection;
