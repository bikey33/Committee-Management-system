import { useMemo } from "react";
import { format } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { apiClient } from "@/api/client";
import { cn } from "@/lib/utils";
import { getRoleConfig } from "@/config/committeeRoleConfig";
import type { Committee } from "@/api/committees";
import PhaseIndicator from "./PhaseIndicator";
import FinalizationSection from "./FinalizationSection";
import {
  Building2,
  Clock,
  Download,
  Eye,
  FileText,
  Fingerprint,
  Info,
  Mail,
  Phone,
  Target,
  User,
  Users,
} from "lucide-react";

interface CommitteeDetailContentProps {
  committee: Committee;
  id: string;
}

const CommitteeDetailContent = ({ committee, id }: CommitteeDetailContentProps) => {
  const { toast } = useToast();

  const getFirstValue = (...values: Array<any>) => {
    for (const value of values) {
      if (value !== null && value !== undefined && value !== "") {
        return value;
      }
    }
    return null;
  };

  const getDateValue = (...values: Array<any>) => {
    const value = getFirstValue(...values);
    return typeof value === "string" ? value : null;
  };

  const formationLetterUrl = getFirstValue(
    committee.formationLetterURL,
    (committee as any).formation_letter,
    (committee as any).formationLetter,
    (committee as any).formation_letter_url,
  );

  const formationDate = getDateValue(committee.formation_date, (committee as any).formationDate);
  const assignedDate = getDateValue(
    (committee as any).assigned_date,
    (committee as any).effective_date,
    (committee as any).assignedDate,
  );
  const deadlineDate = getDateValue(committee.deadline, (committee as any).deadline_date, (committee as any).deadlineDate);

  const getCommitteeDate = (...fields: Array<string | null | undefined>) => {
    for (const field of fields) {
      if (field) return field;
    }
    return null;
  };

  const formatDate = (dateString: string | null | undefined) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return "N/A";

    const month = format(date, "MMMM");
    const day = format(date, "d");
    const suffix = format(date, "do").replace(/[0-9]/g, "");
    const year = format(date, "yyyy");

    return (
      <span>
        {month} {day}<sup className="text-[10px] ml-0.5">{suffix}</sup>, {year}
      </span>
    );
  };

  const formationLetterName = useMemo(() => {
    if (!formationLetterUrl) return "None";
    try {
      return String(formationLetterUrl).split("/").pop() || "Formation Letter";
    } catch {
      return "Formation Letter";
    }
  }, [formationLetterUrl]);

  const handlePreview = async () => {
    try {
      const response = await apiClient.get(`/api/committee/committees/${id}/preview/`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: response.headers["content-type"] });
      const url = window.URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => window.URL.revokeObjectURL(url), 100);
    } catch (error: any) {
      console.error("Failed to preview formation letter:", error);

      let errorMessage = "Failed to preview file.";
      if (error.response?.data instanceof Blob) {
        const text = await error.response.data.text();
        try {
          const json = JSON.parse(text);
          errorMessage = json.message || errorMessage;
        } catch {
          // ignore parse errors
        }
      }

      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const handleDownload = async () => {
    try {
      const response = await apiClient.get(`/api/committee/committees/${id}/download/`, {
        responseType: "blob",
      });
      const blob = new Blob([response.data], { type: response.headers["content-type"] });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;

      const contentDisposition = response.headers["content-disposition"];
      let filename = "formation_letter.pdf";
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
        if (filenameMatch?.[1]) {
          filename = filenameMatch[1];
        }
      }

      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      console.error("Failed to download formation letter:", error);

      let errorMessage = "Failed to download file.";
      if (error.response?.data instanceof Blob) {
        const text = await error.response.data.text();
        try {
          const json = JSON.parse(text);
          errorMessage = json.message || errorMessage;
        } catch {
          // ignore parse errors
        }
      }

      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    }
  };

  const members = Array.isArray(committee.membersList) ? committee.membersList : [];
  const sortedMembers = [...members].sort((a: any, b: any) => {
    const roleA = String(a.role || "").toLowerCase();
    const roleB = String(b.role || "").toLowerCase();
    if (roleA === "co-ordinator" || roleA === "coordinator") return -1;
    if (roleB === "co-ordinator" || roleB === "coordinator") return 1;
    return 0;
  });

  return (
    <div className="flex flex-col bg-white overflow-hidden rounded-xl border border-slate-200 shadow-sm">
      {/* Header */}
      <div className="px-4 py-5 border-b bg-white shrink-0 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-2xl font-bold text-[hsl(209,100%,32%)] tracking-tight">
                {committee.name ? committee.name.charAt(0).toUpperCase() + committee.name.slice(1).toLowerCase() : "Committee Details"}
              </h2>
              <Badge variant="outline" className="text-[10px] h-5 px-2 border-slate-200 text-slate-500 font-bold rounded">
                <span className="capitalize">{String(committee.committee_type || "standard").toLowerCase()}</span> Committee
              </Badge>
            </div>
            <p className="text-sm text-slate-400 font-medium tracking-tight">
              View the details and team information of this committee.
            </p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-6 bg-slate-50/10 sm:p-6 lg:p-8 lg:space-y-8">
        {/* Phase Indicator */}
        {committee.phases && committee.phases.length > 0 && (
          <PhaseIndicator
            phases={committee.phases.map((phase: any) => ({
              phase: phase.phase,
              name: phase.name,
              status: phase.completed ? `Completed 5/15/2026` : phase.phase === 'initialization' ? 'In Progress' : 'Submit report',
              visible: phase.visible !== false
            }))}
            initializationComplete={committee.initialization_phase_completed}
          />
        )}

        {/* Phase 1 - Initialization */}
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-slate-900">Phase 1</h3>
              <p className="text-sm font-semibold text-slate-700 mt-1">Initialization</p>
            </div>
            <Button variant="outline" size="sm">Reopen</Button>
          </div>

          {/* Office Card */}
          <Card className="shadow-sm border-slate-200 rounded-lg">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-2.5 bg-blue-50 rounded-lg text-[hsl(209,100%,32%)]">
                <Building2 className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-bold text-slate-400 tracking-tight mb-0.5">Office / Department</p>
                <p className="text-sm font-bold text-slate-700 leading-tight">{committee.office_name || "Head Office"}</p>
              </div>
            </CardContent>
          </Card>

          {/* Purpose Section */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-700">
              <Target className="h-5 w-5 text-[hsl(209,100%,32%)]" />
              <h3 className="text-sm font-bold tracking-tight">Description (Purpose)</h3>
            </div>
            <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-[hsl(209,100%,32%)]" />
              <p className="text-slate-600 leading-relaxed text-sm font-medium font-serif italic">
                &ldquo;{committee.purpose || "No specific purpose statement provided."}&rdquo;
              </p>
            </div>
          </div>

          {/* Members Section */}
          <div className="space-y-3">
            <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
              <Users className="h-5 w-5 text-[hsl(209,100%,32%)]" />
              <h3 className="text-sm font-bold tracking-tight text-slate-800">
                Committee Members ({members.length})
              </h3>
            </div>

            <div className="space-y-2.5">
              {sortedMembers.length > 0 ? (
                sortedMembers.map((member: any, idx: number) => {
                  const roleConfig = getRoleConfig(member.role || "member");
                  return (
                    <div
                      key={`${member.employeeId || member.id || idx}`}
                      className="bg-white p-3.5 rounded-lg border border-slate-100 shadow-sm transition-all hover:border-[hsl(209,100%,32%)]"
                    >
                      <div className="flex items-center gap-4">
                        <div className="shrink-0 w-11 h-11 rounded-lg bg-blue-50/50 flex items-center justify-center border border-blue-100/50">
                          <User className="h-5.5 w-5.5 text-[hsl(209,100%,32%)]" />
                        </div>

                        <div className="flex-1 min-w-0 space-y-1.5">
                          <div className="flex items-center gap-3 flex-wrap">
                            <h4 className="font-semibold text-slate-800 text-sm leading-tight capitalize tracking-tight">
                              {member.name || "Unnamed Member"}
                            </h4>
                            <Badge className={cn("text-[9px] px-2 py-0.5 font-bold border-0 shadow-none h-5 rounded-full", roleConfig.badgeClasses)}>
                              <span className="capitalize">{roleConfig.label.toLowerCase()}</span>
                            </Badge>
                          </div>

                          <div className="flex flex-wrap items-center gap-y-1 gap-x-6 text-[11px] font-medium text-slate-400">
                            <div className="flex items-center gap-1.5">
                              <Fingerprint className="h-3.5 w-3.5 text-slate-300" />
                              <span>{member.employeeId || member.id || "N/A"}</span>
                            </div>
                            {member.email && (
                              <div className="flex items-center gap-1.5">
                                <Mail className="h-3.5 w-3.5 text-slate-300" />
                                <span className="break-all">{member.email}</span>
                              </div>
                            )}
                            {(member.phone || member.mobile || member.phone_number) && (
                              <div className="flex items-center gap-1.5">
                                <Phone className="h-3.5 w-3.5 text-slate-300" />
                                <span>{member.phone || member.mobile || member.phone_number}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-slate-400 text-sm font-medium">No members have been assigned to this committee.</p>
              )}
            </div>
          </div>

          {/* Dates and Documents Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Dates Card */}
            <Card className="shadow-sm border-slate-200 rounded-lg overflow-hidden">
              <div className="bg-[hsl(209,100%,32%)] px-4 py-2.5 border-b border-white/10 flex items-center gap-2">
                <Clock className="h-4 w-4 text-white" />
                <span className="text-xs font-bold text-white tracking-tight">Dates</span>
              </div>
              <CardContent className="p-5">
                <div className="relative pl-5 space-y-6">
                  {getCommitteeDate(committee.formation_date) && (
                    <div className="relative">
                      <div className="absolute -left-[18px] top-1.5 w-3 h-3 rounded-full border-2 border-white bg-[hsl(209,100%,32%)] shadow-sm" />
                      <div className="space-y-0.5">
                        <p className="text-[10px] font-bold text-slate-400 tracking-tight">Formation Date</p>
                        <p className="text-xs font-bold text-slate-700">{formatDate(getCommitteeDate(committee.formation_date))}</p>
                      </div>
                    </div>
                  )}
                  {getCommitteeDate((committee as any).assigned_date) && (
                    <div className="relative">
                      <div className="absolute -left-[18px] top-1.5 w-3 h-3 rounded-full border-2 border-white bg-blue-500 shadow-sm" />
                      <div className="space-y-0.5">
                        <p className="text-[10px] font-bold text-slate-400 tracking-tight">Effective Date</p>
                        <p className="text-xs font-bold text-blue-600">{formatDate(getCommitteeDate((committee as any).assigned_date))}</p>
                      </div>
                    </div>
                  )}
                  {getCommitteeDate(committee.deadline) && (
                    <div className="relative">
                      <div className="absolute -left-[18px] top-1.5 w-3 h-3 rounded-full border-2 border-white bg-rose-500 shadow-sm" />
                      <div className="space-y-0.5">
                        <p className="text-[10px] font-bold text-slate-400 tracking-tight">Deadline</p>
                        <p className="text-xs font-bold text-rose-600">{formatDate(getCommitteeDate(committee.deadline))}</p>
                      </div>
                    </div>
                  )}
                  {!getCommitteeDate(committee.formation_date) && !getCommitteeDate((committee as any).assigned_date) && !getCommitteeDate(committee.deadline) && (
                    <p className="text-xs text-slate-500 italic">No dates set.</p>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Documents Card */}
            <Card className="shadow-sm border-slate-200 rounded-lg overflow-hidden">
              <div className="bg-[hsl(209,100%,32%)] px-4 py-2.5 border-b border-white/10 flex items-center gap-2">
                <FileText className="h-4 w-4 text-white" />
                <span className="text-xs font-bold text-white tracking-tight">Official Documents</span>
              </div>
              <CardContent className="p-4 space-y-3">
                <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-100 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-[10px] font-bold text-slate-400 tracking-tight mb-0.5">Formation Letter</p>
                    <p className="text-sm font-semibold text-slate-800 truncate">{formationLetterName}</p>
                  </div>
                  {formationLetterUrl ? (
                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="rounded-full hover:bg-[hsl(209,100%,32%)] hover:text-white h-7 w-7"
                        title="Preview"
                        onClick={handlePreview}
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="rounded-full hover:bg-[hsl(209,100%,32%)] hover:text-white h-7 w-7"
                        title="Download"
                        onClick={handleDownload}
                      >
                        <Download className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : null}
                </div>

                {!formationLetterUrl && (
                  <div className="p-4 bg-amber-50/30 rounded-lg border border-amber-100/50 flex gap-3 italic">
                    <Info className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
                    <p className="text-[11px] text-amber-700 leading-tight">None</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Phase 2 - Finalization */}
        {committee.initialization_phase_completed && (
          <FinalizationSection
            committeeId={id}
            isInitializationComplete={committee.initialization_phase_completed}
            onReportSubmit={() => {
              toast({
                title: "Success",
                description: "Report submitted successfully",
              });
            }}
          />
        )}
      </div>

      {/* Footer */}
      <div className="flex shrink-0 justify-end border-t bg-slate-50/50 px-4 py-4 sm:px-6 lg:px-8">
        <Button
          variant="default"
          className="h-9 rounded-md px-6 text-sm font-bold transition-all sm:px-8"
          onClick={() => (window as any).closeModal?.()}
        >
          Close
        </Button>
      </div>
    </div>
  );
};

export default CommitteeDetailContent;
