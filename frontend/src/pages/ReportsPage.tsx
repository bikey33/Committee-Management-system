import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  BarChart3,
  Activity,
  CheckCircle2,
  Clock,
  FolderClock,
  Users,
  ChevronsUpDown,
  Check,
  Star,
  Shield,
  BookOpen,
  UserCheck,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PermissionGate } from "@/components/PermissionGate";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import CommitteeDetailModal from "@/components/committee/CommitteeDetailModal";
import {
  committeesService,
  type MyCommitteeReportItem,
  type Committee,
  type StalledCommittee,
} from "@/api/committees";
import { usersService, type User as UserModel } from "@/api/users";
import { authService } from "@/api/auth";
import { cn } from "@/lib/utils";

// Theme-friendly chart palette (NT blue primary + status colors).
const COLORS = ["hsl(209 100% 32%)", "#059669", "#f59e0b", "#e11d48", "#64748b", "#7c3aed"];

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Card className="border-border/60 shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="h-4 w-4 text-primary" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-foreground">{value}</div>
      </CardContent>
    </Card>
  );
}

const capitalize = (s?: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : "");

export function ReportsPage() {
  const [detailId, setDetailId] = useState<string | null>(null);

  const { data: user } = useQuery({ queryKey: ["userMe"], queryFn: authService.getMe });
  const employeeId = (user as any)?.employeeId || (user as any)?.employee_id;

  const { data: myReport } = useQuery({
    queryKey: ["my-committees-report", employeeId],
    queryFn: committeesService.getMyCommitteesReport,
    enabled: !!employeeId,
  });

  const { data: stats } = useQuery({
    queryKey: ["committee-stats"],
    queryFn: () => committeesService.getCommitteeStats(),
  });

  const { data: officeCommittees = [] } = useQuery({
    queryKey: ["office-committees"],
    queryFn: () => committeesService.getOfficeCommittees(),
  });

  const statusData = (stats?.by_status ?? []).map((s) => ({
    name: capitalize(s.committee_status),
    value: s.count,
  }));
  const typeData = (stats?.by_type ?? []).map((s) => ({
    name: capitalize(s.committee_type),
    count: s.count,
  }));
  const isOrg = stats?.scope === "org" || stats?.scope === "office";

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="min-w-0">
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          <BarChart3 size={28} className="text-primary" />
          Reports
        </h1>
        <p className="text-muted-foreground mt-1">
          Your committee involvement and {isOrg ? "organization-wide" : "your office's"} overview
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid gap-4 grid-cols-2 xl:grid-cols-4">
        <StatCard label="My Active" value={myReport?.counts.active ?? 0} icon={Activity} />
        <StatCard label="My Past" value={myReport?.counts.past ?? 0} icon={FolderClock} />
        <StatCard
          label={isOrg ? "Open (org)" : "Open"}
          value={stats?.totals.open ?? 0}
          icon={CheckCircle2}
        />
        <StatCard
          label={isOrg ? "Overdue (org)" : "Overdue"}
          value={stats?.totals.overdue ?? 0}
          icon={Clock}
        />
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">By status</CardTitle>
          </CardHeader>
          <CardContent className="h-[260px]">
            {statusData.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2}>
                    {statusData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">By type</CardTitle>
          </CardHeader>
          <CardContent className="h-[260px]">
            {typeData.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={typeData}>
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="hsl(209 100% 32%)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

      </div>

      {/* Lists */}
      <Tabs defaultValue="active" className="w-full">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="active">My Active ({myReport?.counts.active ?? 0})</TabsTrigger>
          <TabsTrigger value="past">My Past ({myReport?.counts.past ?? 0})</TabsTrigger>
          <TabsTrigger value="office">My Office ({officeCommittees.length})</TabsTrigger>
          <PermissionGate codename="committee.view_cross_office">
            <TabsTrigger value="userwise" className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5" />
              User-wise
            </TabsTrigger>
          </PermissionGate>
          <PermissionGate codename="committee.view_cross_office">
            <TabsTrigger value="stalled" className="flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5" />
              Stalled
            </TabsTrigger>
          </PermissionGate>
        </TabsList>

        <TabsContent value="active">
          <MyCommitteeTable
            items={myReport?.active ?? []}
            onView={setDetailId}
            emptyText="You're not currently in any active committee."
          />
        </TabsContent>
        <TabsContent value="past">
          <MyCommitteeTable
            items={myReport?.past ?? []}
            onView={setDetailId}
            showReason
            emptyText="No past committees yet."
          />
        </TabsContent>
        <TabsContent value="office">
          <OfficeCommitteeTable committees={officeCommittees} onView={setDetailId} />
        </TabsContent>
        <PermissionGate codename="committee.view_cross_office">
          <TabsContent value="userwise">
            <UserWiseReport onView={setDetailId} />
          </TabsContent>
        </PermissionGate>
        <PermissionGate codename="committee.view_cross_office">
          <TabsContent value="stalled">
            <StalledCommitteesReport onView={setDetailId} />
          </TabsContent>
        </PermissionGate>
      </Tabs>

      <CommitteeDetailModal id={detailId} isOpen={!!detailId} onClose={() => setDetailId(null)} />
    </div>
  );
}

function StatusBadge({ item }: { item: MyCommitteeReportItem }) {
  if (item.is_closed) {
    return <Badge variant="outline" className="rounded-full px-3 text-muted-foreground">Closed</Badge>;
  }
  if (item.is_overdue) {
    return <Badge className="rounded-full px-3 bg-rose-600 text-white border-transparent hover:bg-rose-700">Overdue</Badge>;
  }
  return <Badge className="rounded-full px-3 bg-emerald-600 text-white border-transparent hover:bg-emerald-700">Active</Badge>;
}

function MyCommitteeTable({
  items,
  onView,
  showReason,
  emptyText,
}: {
  items: MyCommitteeReportItem[];
  onView: (id: string) => void;
  showReason?: boolean;
  emptyText: string;
}) {
  return (
    <div className="border rounded-xl bg-card shadow-sm overflow-hidden">
      <div className="w-full overflow-x-auto">
        <Table className="min-w-[720px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[260px]">Committee</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>My Role</TableHead>
              <TableHead>Office</TableHead>
              <TableHead>Status</TableHead>
              {showReason && <TableHead>Reason</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={showReason ? 6 : 5} className="text-center py-8 text-muted-foreground">
                  {emptyText}
                </TableCell>
              </TableRow>
            ) : (
              items.map((c) => (
                <TableRow
                  key={c.committee_id}
                  onClick={() => onView(String(c.committee_id))}
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                >
                  <TableCell className="font-medium text-foreground py-4">{c.name}</TableCell>
                  <TableCell className="capitalize text-muted-foreground">{c.committee_type}</TableCell>
                  <TableCell className="capitalize text-muted-foreground">{c.my_role || "—"}</TableCell>
                  <TableCell className="text-muted-foreground">{c.office_name || "N/A"}</TableCell>
                  <TableCell><StatusBadge item={c} /></TableCell>
                  {showReason && (
                    <TableCell>
                      {c.left_reason === "removed" ? (
                        <Badge variant="outline" className="rounded-full px-3 text-rose-600 border-rose-200">Removed</Badge>
                      ) : c.left_reason === "closed" ? (
                        <Badge variant="outline" className="rounded-full px-3 text-muted-foreground">Closed</Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function OfficeCommitteeTable({
  committees,
  onView,
}: {
  committees: Committee[];
  onView: (id: string) => void;
}) {
  return (
    <div className="border rounded-xl bg-card shadow-sm overflow-hidden">
      <div className="w-full overflow-x-auto">
        <Table className="min-w-[720px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[260px]">Committee</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Members</TableHead>
              <TableHead>Office</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {committees.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                  No committees in your office.
                </TableCell>
              </TableRow>
            ) : (
              committees.map((c) => (
                <TableRow
                  key={c.id || c._id}
                  onClick={() => onView(String(c.id || c._id))}
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                >
                  <TableCell className="font-medium text-foreground py-4">{c.name}</TableCell>
                  <TableCell className="capitalize text-muted-foreground">{c.committee_type}</TableCell>
                  <TableCell className="text-muted-foreground">{c.members_count ?? 0}</TableCell>
                  <TableCell className="text-muted-foreground">{c.office_name || "N/A"}</TableCell>
                  <TableCell>
                    <Badge
                      className={
                        c.is_closed
                          ? "rounded-full px-3 bg-slate-300 text-slate-700 border-transparent"
                          : c.is_overdue
                          ? "rounded-full px-3 bg-rose-600 text-white border-transparent"
                          : "rounded-full px-3 bg-emerald-600 text-white border-transparent"
                      }
                    >
                      {c.is_closed ? "Closed" : c.is_overdue ? "Overdue" : "Active"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ─── User-wise Report ──────────────────────────────────────────────────────────

const ROLE_CONFIGS = [
  {
    key: "coordinator",
    label: "Coordinator",
    icon: Star,
    cardClass: "border-blue-200 bg-blue-50",
    iconClass: "text-[hsl(209,100%,32%)]",
    valueClass: "text-[hsl(209,100%,32%)]",
    badgeClass: "bg-blue-100 text-blue-800 border-blue-200",
  },
  {
    key: "secretary",
    label: "Secretary",
    icon: Shield,
    cardClass: "border-emerald-200 bg-emerald-50",
    iconClass: "text-emerald-600",
    valueClass: "text-emerald-700",
    badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-200",
  },
  {
    key: "subject_expert",
    label: "Subject Expert",
    icon: BookOpen,
    cardClass: "border-amber-200 bg-amber-50",
    iconClass: "text-amber-600",
    valueClass: "text-amber-700",
    badgeClass: "bg-amber-100 text-amber-800 border-amber-200",
  },
  {
    key: "member",
    label: "Member",
    icon: UserCheck,
    cardClass: "border-slate-200 bg-slate-50",
    iconClass: "text-slate-500",
    valueClass: "text-slate-700",
    badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
  },
] as const;

type RoleKey = "all" | "coordinator" | "secretary" | "subject_expert" | "member";

function normalizeRole(role?: string | null): string {
  const r = (role ?? "").toLowerCase().replace(/[\s\-]+/g, "_");
  if (r.includes("coord")) return "coordinator";
  if (r.includes("secret")) return "secretary";
  if (r.includes("subject") || r.includes("expert")) return "subject_expert";
  return "member";
}

function userDisplayName(u: UserModel) {
  return (
    u.name ||
    (u.first_name || u.last_name
      ? `${u.first_name ?? ""} ${u.last_name ?? ""}`.trim()
      : u.username) ||
    u.employee_id
  );
}

function RoleBadge({ role }: { role: string }) {
  const config = ROLE_CONFIGS.find((r) => r.key === normalizeRole(role));
  return (
    <Badge variant="outline" className={cn("rounded-full px-3 font-medium capitalize text-xs", config?.badgeClass)}>
      {role?.replace(/_/g, " ") || "member"}
    </Badge>
  );
}

function UserWiseReport({ onView }: { onView: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserModel | null>(null);
  const [roleFilter, setRoleFilter] = useState<RoleKey>("all");

  const { data: allUsers = [], isLoading: usersLoading } = useQuery({
    queryKey: ["users-all"],
    queryFn: usersService.getAll,
  });

  const empId = selectedUser?.employeeId || selectedUser?.employee_id || "";

  const { data: memberships, isLoading: membershipsLoading, isError: membershipsError } = useQuery({
    queryKey: ["user-memberships", empId],
    queryFn: () => usersService.getUserMemberships(empId),
    enabled: !!empId,
  });

  // Combine active + past into a single list
  const allItems: MyCommitteeReportItem[] = [
    ...(memberships?.active ?? []),
    ...(memberships?.past ?? []),
  ];

  // Role counts
  const roleCounts = ROLE_CONFIGS.reduce(
    (acc, r) => {
      acc[r.key] = allItems.filter((i) => normalizeRole(i.my_role) === r.key).length;
      return acc;
    },
    {} as Record<string, number>
  );

  // Filtered list
  const filtered =
    roleFilter === "all"
      ? allItems
      : allItems.filter((i) => normalizeRole(i.my_role) === roleFilter);

  return (
    <div className="space-y-5">
      {/* User selector */}
      <div className="rounded-xl border border-border/60 bg-card shadow-sm p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">Select User</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Choose a user to view their committee involvement by role
            </p>
          </div>
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="w-full sm:w-[320px] justify-between font-normal text-left"
              >
                {selectedUser ? (
                  <span className="flex items-center gap-2 truncate">
                    <span className="h-5 w-5 rounded-full bg-[hsl(209,100%,32%)] text-white text-[10px] font-bold flex items-center justify-center shrink-0">
                      {userDisplayName(selectedUser).charAt(0).toUpperCase()}
                    </span>
                    <span className="truncate">{userDisplayName(selectedUser)}</span>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {selectedUser.employeeId || selectedUser.employee_id}
                    </span>
                  </span>
                ) : (
                  <span className="text-muted-foreground">
                    {usersLoading ? "Loading users…" : "Search and select a user…"}
                  </span>
                )}
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[320px] p-0" align="start">
              <Command>
                <CommandInput placeholder="Search by name or ID…" />
                <CommandList>
                  <CommandEmpty>No user found.</CommandEmpty>
                  <CommandGroup>
                    {(allUsers as UserModel[]).map((u) => (
                      <CommandItem
                        key={u.employee_id || u.employeeId}
                        value={`${userDisplayName(u)} ${u.employee_id || u.employeeId}`}
                        onSelect={() => {
                          setSelectedUser(u);
                          setRoleFilter("all");
                          setOpen(false);
                        }}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4 shrink-0",
                            selectedUser?.employee_id === u.employee_id
                              ? "opacity-100"
                              : "opacity-0"
                          )}
                        />
                        <span className="flex-1 truncate">{userDisplayName(u)}</span>
                        <span className="ml-2 text-xs text-muted-foreground shrink-0">
                          {u.employee_id || u.employeeId}
                        </span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Placeholder when no user selected */}
      {!selectedUser && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border py-16 text-center">
          <Users className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-sm font-medium text-muted-foreground">
            Select a user above to see their committee involvement
          </p>
        </div>
      )}

      {/* Content after user selection */}
      {selectedUser && (
        <>
          {/* User info bar */}
          <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-card shadow-sm px-5 py-3">
            <div className="h-9 w-9 rounded-full bg-[hsl(209,100%,32%)] text-white text-sm font-bold flex items-center justify-center shrink-0">
              {userDisplayName(selectedUser).charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-foreground truncate">
                {userDisplayName(selectedUser)}
              </p>
              <p className="text-xs text-muted-foreground">
                {selectedUser.employeeId || selectedUser.employee_id}
                {(selectedUser.working_office || selectedUser.office_name) &&
                  ` · ${selectedUser.working_office || selectedUser.office_name}`}
                {(selectedUser.role || selectedUser.user_role?.name) &&
                  ` · ${selectedUser.role || selectedUser.user_role?.name}`}
              </p>
            </div>
            <Badge
              className={
                selectedUser.is_active
                  ? "bg-green-600 text-white border-transparent text-xs"
                  : "bg-slate-300 text-slate-700 border-transparent text-xs"
              }
            >
              {selectedUser.is_active ? "Active" : "Inactive"}
            </Badge>
          </div>

          {/* KPI cards */}
          {membershipsLoading ? (
            <div className="grid gap-4 grid-cols-2 xl:grid-cols-4">
              {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
            </div>
          ) : (
            <div className="grid gap-4 grid-cols-2 xl:grid-cols-4">
              {ROLE_CONFIGS.map(({ key, label, icon: Icon, cardClass, iconClass, valueClass }) => (
                <button
                  key={key}
                  onClick={() => setRoleFilter(roleFilter === key ? "all" : key as RoleKey)}
                  className={cn(
                    "rounded-xl border p-4 text-left transition-all hover:shadow-md",
                    cardClass,
                    roleFilter === key && "ring-2 ring-offset-1 ring-[hsl(209,100%,32%)]"
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-muted-foreground">{label}</span>
                    <Icon className={cn("h-4 w-4", iconClass)} />
                  </div>
                  <p className={cn("text-2xl font-bold", valueClass)}>{roleCounts[key] ?? 0}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    {roleCounts[key] === 1 ? "committee" : "committees"}
                  </p>
                </button>
              ))}
            </div>
          )}

          {/* Role filter pills */}
          {!membershipsLoading && (
            <div className="flex flex-wrap gap-2">
              {(["all", "coordinator", "secretary", "subject_expert", "member"] as RoleKey[]).map(
                (r) => (
                  <button
                    key={r}
                    onClick={() => setRoleFilter(r)}
                    className={cn(
                      "rounded-full px-4 py-1.5 text-sm font-semibold border transition-colors",
                      roleFilter === r
                        ? "bg-[hsl(209,100%,32%)] text-white border-[hsl(209,100%,32%)]"
                        : "bg-background text-muted-foreground border-border hover:border-[hsl(209,100%,32%)] hover:text-[hsl(209,100%,32%)]"
                    )}
                  >
                    {r === "all"
                      ? `All (${allItems.length})`
                      : r === "subject_expert"
                      ? `Subject Expert (${roleCounts[r] ?? 0})`
                      : `${capitalize(r)} (${roleCounts[r] ?? 0})`}
                  </button>
                )
              )}
            </div>
          )}

          {/* Table */}
          {membershipsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 rounded-lg" />)}
            </div>
          ) : membershipsError ? (
            <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-rose-200 bg-rose-50 py-12 text-center">
              <Users className="h-8 w-8 text-rose-300" />
              <p className="text-sm font-medium text-rose-600">Could not load memberships</p>
              <p className="text-xs text-rose-400">
                You may not have permission to view this user's data.
              </p>
            </div>
          ) : (
            <div className="rounded-xl border border-border/60 bg-card shadow-sm overflow-hidden">
              <div className="w-full overflow-x-auto">
                <Table className="min-w-[720px]">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[280px]">Committee</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Office</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Joined</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filtered.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                          {allItems.length === 0
                            ? "This user is not in any committees."
                            : `No committees with role "${roleFilter.replace(/_/g, " ")}".`}
                        </TableCell>
                      </TableRow>
                    ) : (
                      filtered.map((item) => (
                        <TableRow
                          key={item.committee_id}
                          onClick={() => onView(String(item.committee_id))}
                          className="cursor-pointer hover:bg-muted/50 transition-colors"
                        >
                          <TableCell className="font-medium text-foreground py-4">
                            <div>
                              {item.name}
                              {item.left_reason && (
                                <Badge
                                  variant="outline"
                                  className={cn(
                                    "ml-2 rounded-full px-2 text-[10px] font-normal",
                                    item.left_reason === "removed"
                                      ? "border-rose-200 text-rose-500"
                                      : "border-slate-200 text-slate-400"
                                  )}
                                >
                                  {item.left_reason}
                                </Badge>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="capitalize text-muted-foreground">
                            {item.committee_type}
                          </TableCell>
                          <TableCell>
                            <RoleBadge role={item.my_role ?? "member"} />
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {item.office_name || "N/A"}
                          </TableCell>
                          <TableCell>
                            <StatusBadge item={item} />
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {item.joined_at
                              ? new Date(item.joined_at).toLocaleDateString(undefined, {
                                  year: "numeric",
                                  month: "short",
                                  day: "numeric",
                                })
                              : "—"}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Stalled Committees Report ────────────────────────────────────────────────

const DAYS_OPTIONS = [7, 14, 30, 60, 90];

function StalledCommitteesReport({ onView }: { onView: (id: string) => void }) {
  const [days, setDays] = useState(30);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const { data, isLoading, isError } = useQuery({
    queryKey: ["stalled-committees", days],
    queryFn: () => committeesService.getStalledCommittees(days),
  });

  const toggleRow = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const committees: StalledCommittee[] = data?.committees ?? [];

  return (
    <div className="flex flex-col gap-4">
      {/* Days filter */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-medium text-muted-foreground">No activity in the last:</span>
        {DAYS_OPTIONS.map((d) => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={cn(
              "rounded-full px-4 py-1.5 text-sm font-semibold border transition-colors",
              days === d
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-background text-muted-foreground border-border hover:border-primary hover:text-primary"
            )}
          >
            {d} days
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 rounded-lg" />)}
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-rose-200 bg-rose-50 py-12 text-center">
          <AlertTriangle className="h-8 w-8 text-rose-300" />
          <p className="text-sm font-medium text-rose-600">Could not load stalled committees.</p>
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
            <p className="text-sm text-amber-800">
              <span className="font-semibold">{committees.length}</span> committee{committees.length !== 1 ? "s" : ""} stalled — no activity for more than {days} days.
            </p>
          </div>

          <div className="rounded-xl border border-border/60 bg-card shadow-sm overflow-hidden">
            <div className="w-full overflow-x-auto">
              <Table className="min-w-[800px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8"></TableHead>
                    <TableHead className="w-[240px]">Committee</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Office</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Days Stalled</TableHead>
                    <TableHead>Last Activity</TableHead>
                    <TableHead>Deadline</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {committees.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-10 text-muted-foreground">
                        No stalled committees — all are active within the last {days} days.
                      </TableCell>
                    </TableRow>
                  ) : (
                    committees.map((c) => (
                      <>
                        <TableRow
                          key={c.id}
                          className={cn(
                            "cursor-pointer hover:bg-muted/50 transition-colors",
                            c.is_overdue && "bg-rose-50/50"
                          )}
                          onClick={() => toggleRow(c.id)}
                        >
                          <TableCell className="pl-4">
                            {expanded.has(c.id)
                              ? <ChevronDown size={15} className="text-muted-foreground" />
                              : <ChevronRight size={15} className="text-muted-foreground" />}
                          </TableCell>
                          <TableCell
                            className="font-medium text-foreground py-4"
                            onClick={(e) => { e.stopPropagation(); onView(String(c.id)); }}
                          >
                            <span className="hover:underline cursor-pointer">{c.name}</span>
                          </TableCell>
                          <TableCell className="capitalize text-muted-foreground">{c.committee_type}</TableCell>
                          <TableCell className="text-muted-foreground">{c.office ?? "—"}</TableCell>
                          <TableCell>
                            <Badge
                              className={cn(
                                "rounded-full px-3 text-xs capitalize",
                                c.is_overdue
                                  ? "bg-rose-600 text-white border-transparent"
                                  : "bg-amber-500 text-white border-transparent"
                              )}
                            >
                              {c.is_overdue ? "Overdue" : c.committee_status.replace(/_/g, " ")}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <span className={cn(
                              "font-semibold text-sm",
                              c.days_stalled > 60 ? "text-rose-600" : c.days_stalled > 30 ? "text-amber-600" : "text-foreground"
                            )}>
                              {c.days_stalled}d
                            </span>
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {new Date(c.last_activity).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                          </TableCell>
                          <TableCell className="text-sm">
                            {c.deadline
                              ? <span className={c.is_overdue ? "text-rose-600 font-medium" : "text-muted-foreground"}>
                                  {new Date(c.deadline).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                                </span>
                              : <span className="text-muted-foreground">—</span>}
                          </TableCell>
                        </TableRow>
                        {expanded.has(c.id) && (
                          <TableRow key={`${c.id}-members`} className="bg-accent/20">
                            <TableCell />
                            <TableCell colSpan={7} className="py-2 pl-8">
                              <p className="text-xs font-semibold text-muted-foreground mb-1.5">
                                Members ({c.member_count})
                              </p>
                              <div className="flex flex-wrap gap-2">
                                {c.members.length === 0
                                  ? <span className="text-xs text-muted-foreground italic">No active members</span>
                                  : c.members.map((m) => (
                                      <span key={m.employee_id} className="text-xs rounded-full border border-border bg-background px-2.5 py-1">
                                        <span className="font-medium">{m.name}</span>
                                        <span className="ml-1 text-muted-foreground capitalize">· {m.role.replace(/_/g, " ")}</span>
                                      </span>
                                    ))}
                              </div>
                            </TableCell>
                          </TableRow>
                        )}
                      </>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
