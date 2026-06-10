import { useMemo, useState } from "react";
import type { Committee } from "@/api/committees";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, Eye, Users, Pencil, Trash2 } from "lucide-react";

interface Props {
  committees: Committee[];
  defaultPageSize?: number;
  onView: (id: string) => void;
  onEdit: (committee: Committee) => void;
  onManageMembers: (committee: Committee) => void;
  onDelete: (committee: Committee) => void;
}

const committeeId = (c: Committee) => c.id || c._id || "";

const CommitteeListTable = ({
  committees,
  defaultPageSize = 10,
  onView,
  onEdit,
  onManageMembers,
  onDelete,
}: Props) => {
  const [search, setSearch] = useState("");
  const [officeFilter, setOfficeFilter] = useState<string>("all");
  const [page, setPage] = useState(1);
  const pageSize = defaultPageSize;

  // Office dropdown options: distinct, non-empty office names present in the data.
  const officeOptions = useMemo(() => {
    const names = new Set<string>();
    (committees || []).forEach((c) => {
      if (c.office_name) names.add(c.office_name);
    });
    return Array.from(names).sort((a, b) => a.localeCompare(b));
  }, [committees]);

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase();
    return (committees || []).filter((c) => {
      const matchesSearch =
        !s ||
        (c.name || "").toLowerCase().includes(s) ||
        (c.purpose || "").toLowerCase().includes(s);
      const matchesOffice = officeFilter === "all" || c.office_name === officeFilter;
      return matchesSearch && matchesOffice;
    });
  }, [committees, search, officeFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const start = (currentPage - 1) * pageSize;
  const current = filtered.slice(start, start + pageSize);

  const onSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const onOfficeChange = (value: string) => {
    setOfficeFilter(value);
    setPage(1);
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar: search + office filter */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1 sm:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by name or purpose…"
            className="pl-9"
          />
        </div>
        <Select value={officeFilter} onValueChange={onOfficeChange}>
          <SelectTrigger className="w-full sm:w-[260px]">
            <SelectValue placeholder="All offices" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All offices</SelectItem>
            {officeOptions.map((name) => (
              <SelectItem key={name} value={name}>
                {name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="border rounded-xl bg-card shadow-sm overflow-hidden">
        <div className="w-full overflow-x-auto">
          <Table className="min-w-[920px]">
            <TableHeader>
              <TableRow>
                <TableHead className="w-[250px]">Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Office</TableHead>
                <TableHead>Members</TableHead>
                <TableHead>Formation Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right pr-6">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {current.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No committees match your filters.
                  </TableCell>
                </TableRow>
              ) : (
                current.map((committee) => (
                  <TableRow
                    key={committeeId(committee) || committee.name}
                    onClick={() => onView(committeeId(committee))}
                    className="cursor-pointer hover:bg-muted/50 transition-colors"
                  >
                    <TableCell className="font-medium text-foreground py-4">
                      {committee.name}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className="bg-background text-foreground border-border font-normal capitalize"
                      >
                        {committee.committee_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {committee.office_name || "N/A"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {committee.members_count || 0}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {committee.formation_date || "Not set"}
                    </TableCell>
                    <TableCell>
                      <Badge className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium border-transparent rounded-full px-3 capitalize">
                        {committee.committee_status || committee.status || "Active"}
                      </Badge>
                    </TableCell>
                    <TableCell
                      className="text-right pr-6"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-3">
                        <button
                          onClick={() => onView(committeeId(committee))}
                          className="text-muted-foreground hover:text-primary transition-colors"
                          title="View Details"
                        >
                          <Eye size={18} />
                        </button>
                        <button
                          onClick={() => onManageMembers(committee)}
                          className="text-muted-foreground hover:text-primary transition-colors"
                          title="Manage Members"
                        >
                          <Users size={18} />
                        </button>
                        <button
                          onClick={() => onEdit(committee)}
                          className="text-muted-foreground hover:text-foreground transition-colors"
                          title="Edit Committee"
                        >
                          <Pencil size={18} />
                        </button>
                        <button
                          onClick={() => onDelete(committee)}
                          className="text-destructive/80 hover:text-destructive transition-colors"
                          title="Delete Committee"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination */}
        {filtered.length > 0 && (
          <div className="flex flex-col items-center justify-between gap-3 border-t border-border px-4 py-3 sm:flex-row">
            <p className="text-sm text-muted-foreground">
              Showing <span className="font-medium text-foreground">{start + 1}</span>–
              <span className="font-medium text-foreground">
                {Math.min(start + pageSize, filtered.length)}
              </span>{" "}
              of <span className="font-medium text-foreground">{filtered.length}</span>
            </p>
            {totalPages > 1 && (
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8"
                  disabled={currentPage <= 1}
                  onClick={() => setPage(currentPage - 1)}
                >
                  Prev
                </Button>
                <span className="px-2 text-sm text-muted-foreground">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8"
                  disabled={currentPage >= totalPages}
                  onClick={() => setPage(currentPage + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CommitteeListTable;
