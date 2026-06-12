import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { PermissionGate } from "@/components/PermissionGate";
import { CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { CheckCircle2, FileText, Trash2, Upload, X } from "lucide-react";
import { toast } from "sonner";
import { committeesService } from "@/api/committees";

interface InProgressSectionProps {
  committeeId: string;
  onTransitioned: () => void;
}

export function InProgressSection({ committeeId, onTransitioned }: InProgressSectionProps) {
  const queryClient = useQueryClient();

  // document upload (ongoing work)
  const fileInputRef = useRef<HTMLInputElement>(null);

  // completion dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [remarks, setRemarks] = useState("");
  const [completionFiles, setCompletionFiles] = useState<File[]>([]);
  const completionFileInputRef = useRef<HTMLInputElement>(null);
  const [submitting, setSubmitting] = useState(false);

  // ── ongoing documents ──────────────────────────────────────────────────────
  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["committee-docs", committeeId],
    queryFn: () => committeesService.getDocuments(committeeId),
    enabled: !!committeeId,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => committeesService.uploadDocument(committeeId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["committee-docs", committeeId] });
      toast.success("File uploaded");
    },
    onError: () => toast.error("Failed to upload file"),
  });

  const deleteMutation = useMutation({
    mutationFn: (docId: number) => committeesService.deleteDocument(committeeId, docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["committee-docs", committeeId] });
      toast.success("File removed");
    },
    onError: () => toast.error("Failed to remove file"),
  });

  const handleOngoingFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).forEach((f) => uploadMutation.mutate(f));
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ── completion dialog ──────────────────────────────────────────────────────
  const handleCompletionFiles = (files: FileList | null) => {
    if (!files) return;
    setCompletionFiles((prev) => [...prev, ...Array.from(files)]);
    if (completionFileInputRef.current) completionFileInputRef.current.value = "";
  };

  const removeCompletionFile = (index: number) => {
    setCompletionFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmitCompletion = async () => {
    setSubmitting(true);
    try {
      // upload completion documents first (if any)
      await Promise.all(
        completionFiles.map((file) => committeesService.uploadDocument(committeeId, file))
      );
      // transition status with remarks
      await committeesService.transitionStatus(committeeId, "completed", remarks);
      queryClient.invalidateQueries({ queryKey: ["committee", committeeId] });
      queryClient.invalidateQueries({ queryKey: ["committees"] });
      queryClient.invalidateQueries({ queryKey: ["committee-docs", committeeId] });
      toast.success("Committee marked as completed");
      setDialogOpen(false);
      onTransitioned();
    } catch {
      toast.error("Failed to complete committee");
    } finally {
      setSubmitting(false);
    }
  };

  const openDialog = () => {
    setRemarks("");
    setCompletionFiles([]);
    setDialogOpen(true);
  };

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <div className="rounded-lg border border-slate-200 bg-white overflow-hidden shadow-sm">
        {/* Phase header */}
        <div className="flex items-center justify-between gap-4 bg-[hsl(209,100%,32%)] px-6 py-4">
          <div>
            <h3 className="text-base font-semibold text-white">In Progress</h3>
          </div>
          <PermissionGate codename="committee.manage">
            <Button
              size="sm"
              onClick={openDialog}
              className="bg-white text-[hsl(209,100%,32%)] hover:bg-blue-50 font-bold border-0 shrink-0"
            >
              <CheckCircle2 className="h-4 w-4 mr-1.5" />
              Mark as Completed
            </Button>
          </PermissionGate>
        </div>

        <CardContent className="p-6 space-y-5">
          {/* Ongoing document uploads */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <FileText className="h-4 w-4 text-[hsl(209,100%,32%)]" />
              <span className="text-sm font-semibold text-slate-800">Documents</span>
              <span className="text-xs text-slate-400">
                ({docs.length} file{docs.length !== 1 ? "s" : ""})
              </span>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => handleOngoingFiles(e.target.files)}
                accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
              />
            </div>

            {isLoading ? (
              <p className="text-sm text-slate-400 py-4 text-center">Loading files…</p>
            ) : docs.length === 0 ? (
              <div
                className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-200 py-8 cursor-pointer hover:border-[hsl(209,100%,32%)] transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-8 w-8 text-slate-300" />
                <p className="text-sm font-medium text-slate-400">Click to upload files</p>
                <p className="text-xs text-slate-300">PDF, DOC, DOCX, XLS, images</p>
              </div>
            ) : (
              <div className="space-y-2">
                {docs.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3"
                  >
                    <FileText className="h-4 w-4 text-[hsl(209,100%,32%)] shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800 truncate">{doc.name}</p>
                      {doc.uploaded_by && (
                        <p className="text-[11px] text-slate-400">{doc.uploaded_by}</p>
                      )}
                    </div>
                    <button
                      onClick={() => committeesService.viewDocument(committeeId, doc.id)}
                      className="text-xs font-medium text-[hsl(209,100%,32%)] hover:underline shrink-0"
                    >
                      View
                    </button>
                    <PermissionGate codename="committee.manage">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-7 w-7 text-slate-400 hover:text-destructive hover:bg-destructive/10 shrink-0"
                        onClick={() => deleteMutation.mutate(doc.id)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </PermissionGate>
                  </div>
                ))}

                <PermissionGate codename="committee.manage">
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full flex items-center justify-center gap-2 rounded-lg border border-dashed border-slate-200 py-2.5 text-xs font-medium text-slate-400 hover:border-[hsl(209,100%,32%)] hover:text-[hsl(209,100%,32%)] transition-colors"
                  >
                    <Upload className="h-3.5 w-3.5" />
                    Add more files
                  </button>
                </PermissionGate>
              </div>
            )}
          </div>
        </CardContent>
      </div>

      {/* ── Mark as Completed dialog ────────────────────────────────────────── */}
      <Dialog open={dialogOpen} onOpenChange={(open) => !submitting && setDialogOpen(open)}>
        <DialogContent className="w-[95vw] max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-[hsl(209,100%,32%)]">
              <CheckCircle2 className="h-5 w-5" />
              Complete Committee
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-5 py-2">
            {/* Remarks */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-800">
                Remarks / Summary
                <span className="ml-1 text-xs font-normal text-slate-400">(optional)</span>
              </label>
              <textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Outcome, key findings, recommendations…"
                rows={4}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[hsl(209,100%,32%)] focus:border-transparent resize-none"
              />
            </div>

            {/* Final document upload */}
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-800">
                Attach Final Documents
                <span className="ml-1 text-xs font-normal text-slate-400">(optional)</span>
              </label>

              {completionFiles.length > 0 && (
                <div className="space-y-1.5 mb-2">
                  {completionFiles.map((file, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2"
                    >
                      <FileText className="h-3.5 w-3.5 text-[hsl(209,100%,32%)] shrink-0" />
                      <span className="flex-1 text-xs font-medium text-slate-700 truncate">
                        {file.name}
                      </span>
                      <span className="text-[10px] text-slate-400 shrink-0">
                        {(file.size / 1024).toFixed(0)} KB
                      </span>
                      <button
                        onClick={() => removeCompletionFile(i)}
                        className="text-slate-400 hover:text-destructive shrink-0"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={() => completionFileInputRef.current?.click()}
                className="w-full flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-200 py-3 text-xs font-medium text-slate-400 hover:border-[hsl(209,100%,32%)] hover:text-[hsl(209,100%,32%)] transition-colors"
              >
                <Upload className="h-4 w-4" />
                Choose files to attach
              </button>
              <input
                ref={completionFileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => handleCompletionFiles(e.target.files)}
                accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setDialogOpen(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSubmitCompletion}
              disabled={submitting}
              className="bg-[hsl(209,100%,32%)] hover:bg-[hsl(209,100%,25%)] text-white font-bold"
            >
              <CheckCircle2 className="h-4 w-4 mr-1.5" />
              {submitting ? "Completing…" : "Mark as Completed"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default InProgressSection;
