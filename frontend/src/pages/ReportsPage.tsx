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
import { BarChart3, Activity, CheckCircle2, Clock, FolderClock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import CommitteeDetailModal from "@/components/committee/CommitteeDetailModal";
import {
  committeesService,
  type MyCommitteeReportItem,
  type Committee,
} from "@/api/committees";
import { authService } from "@/api/auth";

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
  const officeData = (stats?.by_office ?? []).map((s) => ({
    name: s.office_name || "Unassigned",
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
      <div className="grid gap-4 lg:grid-cols-3">
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

        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">By office</CardTitle>
          </CardHeader>
          <CardContent className="h-[260px]">
            {officeData.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={officeData} layout="vertical" margin={{ left: 12 }}>
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#059669" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Lists */}
      <Tabs defaultValue="active" className="w-full">
        <TabsList>
          <TabsTrigger value="active">My Active ({myReport?.counts.active ?? 0})</TabsTrigger>
          <TabsTrigger value="past">My Past ({myReport?.counts.past ?? 0})</TabsTrigger>
          <TabsTrigger value="office">My Office ({officeCommittees.length})</TabsTrigger>
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
