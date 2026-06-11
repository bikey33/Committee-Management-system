import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowRight, Building2, Calendar, Users } from "lucide-react";
import { usersService, User as UserModel } from "@/api/users";
import type { MyCommitteeReportItem } from "@/api/committees";
import CommitteeDetailModal from "@/components/committee/CommitteeDetailModal";

interface UserProfileModalProps {
  user: UserModel | null;
  isOpen: boolean;
  onClose: () => void;
}

type ActiveTab = "profile" | "committees";
type CommitteeSubTab = "active" | "past";

function avatarInitial(name: string) {
  return name.trim().charAt(0).toUpperCase();
}

function formatDate(dateStr?: string | null) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    assigned: "Initialization",
    active: "In Progress",
    completed: "Completed",
    dissolved: "Dissolved",
    under_review: "Under Review",
    suspended: "Suspended",
  };
  return map[status] ?? status;
}

function CommitteeRow({
  item,
  onView,
}: {
  item: MyCommitteeReportItem;
  onView: (id: string) => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate">{item.name}</p>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-0.5">
          {item.my_role && (
            <span className="text-[11px] text-slate-500 capitalize">{item.my_role}</span>
          )}
          {item.committee_type && (
            <span className="text-[11px] text-slate-400">{item.committee_type}</span>
          )}
          {item.joined_at && (
            <span className="text-[11px] text-slate-400 flex items-center gap-1">
              <Calendar className="h-2.5 w-2.5" />
              {formatDate(item.joined_at)}
            </span>
          )}
          {item.left_reason && (
            <Badge
              className={
                item.left_reason === "removed"
                  ? "text-[10px] px-1.5 py-0 bg-rose-100 text-rose-700 border-rose-200 font-normal capitalize"
                  : "text-[10px] px-1.5 py-0 bg-slate-100 text-slate-600 border-slate-200 font-normal capitalize"
              }
              variant="outline"
            >
              {item.left_reason}
            </Badge>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <Badge
          className={
            item.is_closed
              ? "text-[10px] px-1.5 py-0 bg-slate-100 text-slate-500 border-slate-200 font-normal"
              : "text-[10px] px-1.5 py-0 bg-blue-50 text-blue-700 border-blue-200 font-normal"
          }
          variant="outline"
        >
          {statusLabel(item.committee_status)}
        </Badge>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 px-2 text-[hsl(209,100%,32%)] hover:bg-blue-50 text-xs font-semibold"
          onClick={() => onView(String(item.committee_id))}
        >
          <ArrowRight className="h-3.5 w-3.5 mr-1" />
          View
        </Button>
      </div>
    </div>
  );
}

export function UserProfileModal({ user, isOpen, onClose }: UserProfileModalProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>("profile");
  const [subTab, setSubTab] = useState<CommitteeSubTab>("active");
  const [committeeDetailId, setCommitteeDetailId] = useState<string | null>(null);

  const employeeId = user?.employeeId || user?.employee_id || "";
  const displayName =
    user?.name ||
    (user?.first_name || user?.last_name
      ? `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim()
      : user?.username) ||
    "Unknown";

  const { data: memberships, isLoading: membershipsLoading, isError: membershipsError } = useQuery({
    queryKey: ["user-memberships", employeeId],
    queryFn: () => usersService.getUserMemberships(employeeId),
    enabled: isOpen && activeTab === "committees" && !!employeeId,
  });

  const activeItems = memberships?.active ?? [];
  const pastItems = memberships?.past ?? [];

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="w-[95vw] max-w-2xl max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden rounded-2xl">
          <DialogHeader className="sr-only">
            <DialogTitle>User Profile</DialogTitle>
          </DialogHeader>

          {/* Header */}
          <div className="bg-[hsl(209,100%,32%)] px-6 py-5 flex items-center gap-4 shrink-0">
            <div className="h-12 w-12 rounded-full bg-white/20 flex items-center justify-center text-white text-xl font-bold shrink-0">
              {avatarInitial(displayName)}
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-lg font-bold text-white leading-tight truncate">{displayName}</h2>
              <p className="text-sm text-blue-100">{employeeId}</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-slate-200 bg-white shrink-0">
            {(["profile", "committees"] as ActiveTab[]).map((tab) => (
              <button
                key={tab}
                className={`px-5 py-3 text-sm font-semibold capitalize transition-colors border-b-2 -mb-px ${
                  activeTab === tab
                    ? "border-[hsl(209,100%,32%)] text-[hsl(209,100%,32%)]"
                    : "border-transparent text-slate-500 hover:text-slate-800"
                }`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === "committees"
                  ? `Committees${memberships ? ` (${memberships.counts.active})` : ""}`
                  : "Profile"}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === "profile" && user && (
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {[
                  { label: "Full Name", value: displayName },
                  { label: "Employee ID", value: employeeId },
                  { label: "Email", value: user.email || "N/A" },
                  {
                    label: "Office",
                    value: user.working_office || user.office_name || "N/A",
                    icon: <Building2 className="h-3.5 w-3.5" />,
                  },
                  { label: "Role", value: user.role || (user.user_role?.name ?? "User") },
                  { label: "Status", value: user.is_active ? "Active" : "Inactive" },
                ].map(({ label, value, icon }) => (
                  <div key={label} className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
                    <dt className="text-xs text-slate-400 mb-0.5">{label}</dt>
                    <dd className="text-sm font-medium text-slate-800 flex items-center gap-1.5">
                      {icon}
                      {label === "Status" ? (
                        <Badge
                          className={
                            user.is_active
                              ? "bg-green-600 text-white border-transparent text-xs font-medium"
                              : "bg-slate-300 text-slate-700 border-transparent text-xs font-medium"
                          }
                        >
                          {value}
                        </Badge>
                      ) : label === "Role" ? (
                        <Badge variant="outline" className="text-xs font-normal capitalize border-slate-200">
                          {value}
                        </Badge>
                      ) : (
                        value
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            )}

            {activeTab === "committees" && (
              <div className="space-y-4">
                {/* Sub-tabs */}
                <div className="flex gap-1 bg-slate-100 rounded-lg p-1 w-fit">
                  {(["active", "past"] as CommitteeSubTab[]).map((sub) => (
                    <button
                      key={sub}
                      className={`px-4 py-1.5 rounded-md text-sm font-semibold capitalize transition-colors ${
                        subTab === sub
                          ? "bg-white text-[hsl(209,100%,32%)] shadow-sm"
                          : "text-slate-500 hover:text-slate-700"
                      }`}
                      onClick={() => setSubTab(sub)}
                    >
                      {sub === "active"
                        ? `Active (${memberships?.counts.active ?? 0})`
                        : `Past (${memberships?.counts.past ?? 0})`}
                    </button>
                  ))}
                </div>

                {membershipsLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} className="h-16 w-full rounded-lg" />
                    ))}
                  </div>
                ) : membershipsError ? (
                  <div className="flex flex-col items-center gap-2 py-10 text-center">
                    <Users className="h-8 w-8 text-slate-300" />
                    <p className="text-sm text-slate-500">Could not load committee memberships.</p>
                    <p className="text-xs text-slate-400">You may not have permission to view this.</p>
                  </div>
                ) : (
                  <>
                    {subTab === "active" && (
                      <>
                        {activeItems.length === 0 ? (
                          <div className="flex flex-col items-center gap-2 py-10 text-center">
                            <Users className="h-8 w-8 text-slate-300" />
                            <p className="text-sm text-slate-500">Not in any active committees.</p>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {activeItems.map((item) => (
                              <CommitteeRow
                                key={item.committee_id}
                                item={item}
                                onView={setCommitteeDetailId}
                              />
                            ))}
                          </div>
                        )}
                      </>
                    )}
                    {subTab === "past" && (
                      <>
                        {pastItems.length === 0 ? (
                          <div className="flex flex-col items-center gap-2 py-10 text-center">
                            <Users className="h-8 w-8 text-slate-300" />
                            <p className="text-sm text-slate-500">No past committee memberships.</p>
                          </div>
                        ) : (
                          <div className="space-y-2">
                            {pastItems.map((item) => (
                              <CommitteeRow
                                key={item.committee_id}
                                item={item}
                                onView={setCommitteeDetailId}
                              />
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <CommitteeDetailModal
        id={committeeDetailId}
        isOpen={!!committeeDetailId}
        onClose={() => setCommitteeDetailId(null)}
      />
    </>
  );
}

export default UserProfileModal;
