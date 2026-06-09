import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { committeesService } from "../api/committees";
import type { Committee } from "../api/committees";
import { authService } from "../api/auth";
import { useNavigate } from "react-router-dom";
import { CalendarDays, Users, ClipboardList, ArrowRight } from "lucide-react";
import CommitteeDetailModal from "../components/committee/CommitteeDetailModal";

type DashboardUser = {
  employeeId?: string;
  employee_id?: string;
  name?: string;
  username?: string;
};

export function DashboardPage() {
  const navigate = useNavigate();
  const [showCommittees, setShowCommittees] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);

  const { data: user } = useQuery({
    queryKey: ["userMe"],
    queryFn: authService.getMe,
  });

  const currentUser = user as DashboardUser | undefined;
  const employeeId = currentUser?.employeeId || currentUser?.employee_id;

  const { data: committees = [], isLoading, isError } = useQuery({
    queryKey: ["my-committees", employeeId],
    queryFn: () => committeesService.getByMember(String(employeeId)),
    enabled: !!employeeId,
  });

  const activeCommittees = useMemo(() => {
    return committees.filter((committee: Committee) => {
      const status = (committee.committee_status || committee.status || "").toLowerCase();
      return status === "active";
    });
  }, [committees]);

  const totalCommittees = committees.length;

  const roleInCommittee = (committee: Committee) =>
    committee.membersList?.find((m) => m.employeeId === employeeId)?.role;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Dashboard
        </h1>
        <p className="text-muted-foreground">
          Welcome back{currentUser?.name ? `, ${currentUser.name}` : ""}. Here are the active committees you belong to.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Card
          role="button"
          tabIndex={0}
          onClick={() => setShowCommittees(true)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              setShowCommittees(true);
            }
          }}
          className="cursor-pointer border-border/60 shadow-sm transition-colors hover:border-primary/40 hover:bg-accent/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Committees</CardTitle>
            <ClipboardList className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{totalCommittees}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Committees linked to your account · <span className="text-primary">click to view</span>
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Committees</CardTitle>
            <Users className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">{activeCommittees.length}</div>
            <p className="text-xs text-muted-foreground mt-1">Currently active assignments</p>
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm sm:col-span-2 xl:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Current Member</CardTitle>
            <CalendarDays className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-sm font-semibold text-foreground">{currentUser?.name || currentUser?.username || "User"}</div>
            <p className="text-xs text-muted-foreground mt-1">{employeeId || "No employee ID found"}</p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 shadow-sm">
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-lg font-semibold">Active Committees</CardTitle>
            <p className="text-sm text-muted-foreground">The committees you are currently assigned to</p>
          </div>
          <button
            type="button"
            onClick={() => navigate("/committees")}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            View all
            <ArrowRight className="h-4 w-4" />
          </button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
              Loading your committees...
            </div>
          ) : isError ? (
            <div className="rounded-lg border border-dashed border-destructive/40 p-6 text-sm text-destructive">
              Could not load your committees.
            </div>
          ) : activeCommittees.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
              No active committees found for your account.
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {activeCommittees.map((committee: Committee) => (
                <div key={committee.id || committee._id || committee.name} className="rounded-xl border border-border bg-background p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="truncate text-base font-semibold text-foreground">{committee.name}</h3>
                      <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                        {committee.purpose}
                      </p>
                    </div>
                    <Badge className="shrink-0 bg-primary/10 text-primary hover:bg-primary/10 capitalize">
                      {committee.committee_status || committee.status || "active"}
                    </Badge>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span className="rounded-full bg-muted px-2.5 py-1">
                      Type: {committee.committee_type}
                    </span>
                    <span className="rounded-full bg-muted px-2.5 py-1">
                      Members: {committee.members_count ?? 0}
                    </span>
                    <span className="rounded-full bg-muted px-2.5 py-1">
                      Office: {committee.office_name || "N/A"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={showCommittees} onOpenChange={setShowCommittees}>
        <DialogContent className="max-h-[80vh] w-[95vw] max-w-[640px] overflow-y-auto sm:w-full">
          <DialogHeader>
            <DialogTitle>
              My Committees{totalCommittees ? ` (${totalCommittees})` : ""}
            </DialogTitle>
          </DialogHeader>
          {totalCommittees === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              You are not a member of any committee yet.
            </p>
          ) : (
            <div className="flex flex-col gap-2 py-2">
              {committees.map((committee: Committee) => {
                const role = roleInCommittee(committee);
                return (
                  <button
                    key={committee.id || committee._id || committee.name}
                    type="button"
                    onClick={() => {
                      const cid = committee.id || committee._id;
                      if (!cid) return;
                      setShowCommittees(false);
                      setDetailId(String(cid));
                    }}
                    className="flex items-start justify-between gap-3 rounded-lg border border-border bg-background p-3 text-left transition-colors hover:bg-accent"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-foreground">{committee.name}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground capitalize">
                        {committee.committee_type}
                        {committee.office_name ? ` · ${committee.office_name}` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      {role && (
                        <Badge className="bg-primary/10 text-primary hover:bg-primary/10 capitalize">
                          {role}
                        </Badge>
                      )}
                      <Badge variant="outline" className="capitalize">
                        {committee.committee_status || committee.status || "active"}
                      </Badge>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </DialogContent>
      </Dialog>

      <CommitteeDetailModal
        id={detailId}
        isOpen={!!detailId}
        onClose={() => setDetailId(null)}
      />
    </div>
  );
}
