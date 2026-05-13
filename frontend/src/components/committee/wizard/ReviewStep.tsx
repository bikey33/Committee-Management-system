import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  FileText,
  Users,
  Calendar,
  Clock,
  Building,
  Mail,
  Phone,
  User,
  CheckCircle,
  CreditCard
} from "lucide-react";
import { cn } from "@/lib/utils";
import { format, addDays } from "date-fns";
import type { CommitteeMember } from "@/types/committee";
import { getRoleConfig, normalizeRole, isCoordinatorRole, isSecretaryRole, countMembersByRole } from "@/config/committeeRoleConfig";

interface ReviewStepProps {
  name: string;
  purpose: string;
  committeeType: string;
  selectedProcurementPlan: string | null;
  selectedPlanName?: string;
  formDate: string;
  specificationDate: string;
  reviewDate: string;
  members: CommitteeMember[];
  selectedFile: File | null;
  deadlineDays: number;
}

const ReviewStep = ({
  name,
  purpose,
  committeeType,
  selectedProcurementPlan,
  selectedPlanName,
  formDate,
  specificationDate,
  reviewDate,
  members,
  selectedFile,
  deadlineDays,
}: ReviewStepProps) => {
  const roleCount = {
    chairperson: members.filter(m => isCoordinatorRole(m.role)).length,
    secretary: members.filter(m => isSecretaryRole(m.role)).length,
    member: members.filter(m => !isCoordinatorRole(m.role) && !isSecretaryRole(m.role)).length,
  };

  const deadline = formDate ? addDays(new Date(formDate), deadlineDays) : null;

  const getRoleBadgeVariant = (role: string) => {
    return getRoleConfig(role || 'member').badgeClasses;
  };

  const sortedMembers = [...members].sort((a, b) => {
    const roleA = normalizeRole(a.role);
    const roleB = normalizeRole(b.role);
    
    const order = ['chairperson', 'secretary', 'member', 'subject_expert', 'invitee', 'sub_coordinator'];
    const indexA = order.indexOf(roleA);
    const indexB = order.indexOf(roleB);
    
    const sortA = indexA === -1 ? 999 : indexA;
    const sortB = indexB === -1 ? 999 : indexB;
    
    return sortA - sortB;
  });

  const formatDateWithSuperscript = (dateString: string | null | undefined) => {
    if (!dateString) return "Not set";
    try {
      const date = new Date(dateString);
      const day = format(date, "d");
      const monthYear = format(date, "MMMM, yyyy");
      
      const n = parseInt(day);
      let suffix = 'th';
      if (n % 10 === 1 && n % 100 !== 11) suffix = 'st';
      else if (n % 10 === 2 && n % 100 !== 12) suffix = 'nd';
      else if (n % 10 === 3 && n % 100 !== 13) suffix = 'rd';

      return (
        <span>
          {monthYear.split(',')[0]} {day}<sup>{suffix}</sup>, {monthYear.split(',')[1].trim()}
        </span>
      );
    } catch (e) {
      return dateString;
    }
  };

  return (
    <div className="space-y-6">


      <Card className="overflow-hidden border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm">
        <CardHeader className="pb-3 border-b border-slate-50">
          <CardTitle className="text-xs font-bold flex items-center gap-2 text-[hsl(209,100%,32%)] tracking-tight">
            <FileText className="h-4 w-4" />
            Basic Information
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-[11px] font-bold text-slate-400">Committee Name</label>
              <p className="text-lg font-bold text-[hsl(209,100%,32%)] mt-1">{name}</p>
            </div>
            <div>
              <label className="text-[11px] font-bold text-slate-400">Type</label>
              <div className="mt-1">
                <Badge variant="secondary" className="bg-blue-50 text-blue-700 hover:bg-blue-50 text-[10px] font-bold border-none">
                  {committeeType.charAt(0).toUpperCase() + committeeType.slice(1)} Committee
                </Badge>
              </div>
            </div>
          </div>

          <div>
            <label className="text-[11px] font-bold text-slate-400">Purpose & Objectives</label>
            <p className="mt-1.5 text-sm leading-relaxed text-slate-600 text-justify font-medium">{purpose}</p>
          </div>

          {selectedProcurementPlan && (
            <div>
              <label className="text-[11px] font-bold text-slate-400">Procurement Plan</label>
              <p className="mt-1.5 font-bold text-[hsl(209,100%,32%)] text-sm">{selectedPlanName || `Plan ID: ${selectedProcurementPlan}`}</p>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm">
        <CardHeader className="pb-3 border-b border-slate-50">
          <CardTitle className="text-xs font-bold flex items-center gap-2 text-[hsl(209,100%,32%)] tracking-tight">
            <Users className="h-4 w-4" />
            Committee Members ({members.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          {/* Role Summary */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 text-center">
            {countMembersByRole(members).map(({ role, count, config }) => (
              <div key={role} className={`p-3 ${config.cardBg} rounded-xl border ${config.cardBorder} flex flex-col items-center justify-center space-y-1`}>
                <p className={`text-[10px] font-bold ${config.cardTextColor}/70`}>{config.label}</p>
                <p className={`text-xl font-bold ${config.cardCountColor}`}>{count}</p>
              </div>
            ))}
          </div>

          <Separator />

          {/* Members List */}
          <div className="space-y-3">
            {sortedMembers.map((member, index) => (
              <Card key={index} className="border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                <CardContent className="p-4 flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center border border-blue-100 text-blue-600">
                      <User className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-[13px] text-slate-900 truncate tracking-tight">{member.name || 'N/A'}</p>
                      <Badge
                        className={cn(
                          "text-[10px] font-bold py-0.5 px-2.5 rounded-full border-none shadow-sm",
                          getRoleConfig(member.role || 'member').badgeClasses
                        )}
                      >
                        {getRoleConfig(member.role || 'member').label}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                      <div className="flex items-center gap-1.5">
                        <CreditCard className="h-3 w-3 text-slate-400" />
                        <span className="font-medium text-slate-600">{member.employeeId || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Mail className="h-3 w-3 text-slate-400" />
                        <span className="font-medium text-slate-600">{member.email || 'N/A'}</span>
                      </div>
                      {member.phone && (
                        <div className="flex items-center gap-1.5">
                          <Phone className="h-3 w-3 text-slate-400" />
                          <span className="font-medium text-slate-600">{member.phone}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] font-semibold">
                      {member.office && (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-slate-50 text-slate-600 rounded-md border border-slate-100">
                          <Building className="h-3.5 w-3.5 text-slate-400" />
                          <span>Office: {member.office}</span>
                        </div>
                      )}
                      {member.position && (
                        <div className="flex items-center gap-1.5 px-2 py-0.5 bg-blue-50 text-blue-600 rounded-md border border-blue-100">
                          <User className="h-3.5 w-3.5 text-blue-400" />
                          <span>Position: {member.position}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm">
        <CardHeader className="pb-3 border-b border-slate-50">
          <CardTitle className="text-xs font-bold flex items-center gap-2 text-[hsl(209,100%,32%)] tracking-tight">
            <Calendar className="h-4 w-4" />
            Important Dates
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center gap-3 p-3 bg-primary/5 rounded-lg">
              <Calendar className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Formation Date</p>
                <p className="text-sm text-muted-foreground whitespace-nowrap">
                  {formatDateWithSuperscript(formDate)}
                </p>
              </div>
            </div>

            {deadline && (
              <div className="flex items-center gap-3 p-3 bg-orange-50 rounded-lg">
                <Clock className="h-5 w-5 text-orange-600" />
                <div>
                  <p className="font-medium">Deadline</p>
                  <p className="text-sm text-muted-foreground whitespace-nowrap">
                    {formatDateWithSuperscript(deadline.toISOString())} ({deadlineDays} days)
                  </p>
                </div>
              </div>
            )}

            {specificationDate && (
              <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg">
                <FileText className="h-5 w-5 text-blue-600" />
                <div>
                  <p className="font-medium">Specification Submission</p>
                  <p className="text-sm text-muted-foreground whitespace-nowrap">
                    {formatDateWithSuperscript(specificationDate)}
                  </p>
                </div>
              </div>
            )}

            {reviewDate && (
              <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <div>
                  <p className="font-medium">Review Date</p>
                  <p className="text-sm text-muted-foreground whitespace-nowrap">
                    {formatDateWithSuperscript(reviewDate)}
                  </p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Documents */}
      {selectedFile && (
        <Card className="overflow-hidden border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm">
          <CardHeader className="pb-3 border-b border-slate-50">
            <CardTitle className="text-xs font-bold flex items-center gap-2 text-[hsl(209,100%,32%)] tracking-tight">
              <FileText className="h-4 w-4" />
              Documents
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
              <FileText className="h-8 w-8 text-green-600" />
              <div>
                <p className="font-medium">{selectedFile.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB • Formation Letter
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Final Confirmation */}
      <div className="bg-primary/5 border border-primary/20 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <CheckCircle className="h-6 w-6 text-primary mt-0.5" />
          <div>
            <h4 className="font-semibold text-primary mb-2">Ready to Create Committee</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• All committee members will be notified via email</li>
              <li>• Formation letter will be attached to notifications (if uploaded)</li>
              <li>• Committee will be active immediately upon creation</li>
              <li>• You can modify member details and documents after creation</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewStep;