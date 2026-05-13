import { useMemo, useState } from "react";
import { useDebounce } from "@/hooks/useDebounce";
import type { Committee } from "@/types/committee";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useNavigate } from "react-router-dom";
import { Search, Filter, Eye, Edit, ChevronDown, ChevronUp } from "lucide-react";
import { Card } from "@/components/ui/card";

interface Props {
  committees: Committee[];
  defaultPageSize?: number;
  showTypeFilter?: boolean;
}

const CommitteeListTable = ({ committees, defaultPageSize = 10, showTypeFilter = false }: Props) => {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(defaultPageSize);
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const debouncedSearch = useDebounce(search, 300);

  const filtered = useMemo(() => {
    return (committees || []).filter((c: any) => {
      const matchesType = typeFilter === "all" || (c.committee_type === typeFilter);
      const s = debouncedSearch.toLowerCase();
      const matchesSearch = (c.name || "").toLowerCase().includes(s) || (c.purpose || "").toLowerCase().includes(s);
      return matchesType && matchesSearch;
    });
  }, [committees, search, typeFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const start = (page - 1) * pageSize;
  const current = filtered.slice(start, start + pageSize);

  const renderPagination = () => {
    if (filtered.length === 0) return null;

    return (
      <div className="flex flex-col gap-4 py-0 px-2 mt-2 mb-4 md:flex-row md:items-center md:justify-between">
        {/* Left: Entries Info */}
        <div className="text-xs text-slate-500 md:whitespace-nowrap md:min-w-[200px]">
          Showing <span className="font-semibold text-slate-700">{start + 1}</span> to{" "}
          <span className="font-semibold text-slate-700">{Math.min(start + pageSize, filtered.length)}</span> of{" "}
          <span className="font-semibold text-slate-700">{filtered.length}</span> entries
        </div>

        {/* Center: Spacer */}
        <div className="flex-1 hidden justify-center md:flex">
        </div>

        {/* Right: Navigation */}
        <div className="flex flex-wrap items-center gap-1 justify-start md:min-w-[300px] md:justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            className="h-8 px-3 text-slate-400 border-slate-200 hover:bg-slate-50 hover:text-primary rounded font-medium text-xs bg-white shadow-sm"
          >
            « Prev
          </Button>

          <div className="flex items-center gap-1">
            {(() => {
              const pages = [];
              const maxVisible = 5;

              let startPage = Math.max(1, page - 2);
              let endPage = Math.min(totalPages, startPage + maxVisible - 1);

              if (endPage - startPage < maxVisible - 1) {
                startPage = Math.max(1, endPage - maxVisible + 1);
              }

              for (let i = startPage; i <= endPage; i++) {
                pages.push(
                  <Button
                    key={i}
                    variant={page === i ? "default" : "outline"}
                    size="sm"
                    onClick={() => setPage(i)}
                    className={`h-8 w-8 p-0 font-bold transition-all duration-200 rounded text-xs ${page === i
                      ? "bg-primary text-white border-primary hover:bg-primary/90 shadow-md"
                      : "text-slate-600 border-slate-200 hover:bg-slate-50 bg-white shadow-sm"
                      }`}
                  >
                    {i}
                  </Button>
                );
              }
              return pages;
            })()}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            className="h-8 px-3 text-slate-700 border-slate-200 hover:bg-slate-50 hover:text-primary rounded font-medium text-xs bg-white shadow-sm"
          >
            Next »
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Filters Section */}
      <div className="pt-1">
        <div className="relative w-full">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-4 w-4 text-slate-400" />
          </div>
          <Input
            placeholder="Search by name or purpose..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="pl-9 h-10 text-sm border-slate-200 focus:border-primary focus:ring-primary/20 rounded-md w-full bg-white shadow-sm"
          />
        </div>
      </div>

      {renderPagination()}
      <div className="relative -mt-4">

        <Card className="bg-white border rounded-md shadow-sm overflow-hidden mt-4">
          <div className="overflow-x-auto">
            <Table className="min-w-[1100px]">
              <TableHeader className="bg-[hsl(209_100%_32%)] border-b-0 [&_tr:first-child]:rounded-t-lg">
                <TableRow className="hover:bg-transparent border-0 text-white first:rounded-t-lg overflow-hidden">
                  <TableHead className="font-medium text-white px-4 first:rounded-tl-lg w-[60px]">SN</TableHead>
                  <TableHead className="font-medium text-white px-4">Office Name</TableHead>
                  <TableHead className="font-medium text-white px-4">Name</TableHead>
                  <TableHead className="font-medium text-white px-4">Type</TableHead>
                  <TableHead className="text-center font-medium text-white px-4">Members</TableHead>
                  <TableHead className="font-medium text-white px-4">Deadline</TableHead>
                  <TableHead className="text-center font-medium text-white px-4 last:rounded-tr-lg">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {current.map((c: any, index: number) => (
                  <TableRow key={c._id || c.id} className="hover:bg-muted/50 transition-colors duration-200 group border-b border-slate-100 last:border-0 text-sm">
                    <TableCell className="px-4 py-3 text-slate-600 font-medium">
                      {start + index + 1}
                    </TableCell>
                    <TableCell className="text-slate-600 px-4 py-3 whitespace-normal break-words">
                      {c.office_name || "-"}
                    </TableCell>
                    <TableCell className="font-medium text-slate-900 px-4 py-3 cursor-pointer hover:underline" onClick={() => navigate(`/committees/${c._id || c.id}`)}>
                      {c.name || "-"}
                    </TableCell>
                    <TableCell className="capitalize text-slate-600 px-4 py-3">{c.committee_type || "-"}</TableCell>
                    <TableCell className="text-center px-4 py-3">
                      <span className="bg-slate-100 text-slate-700 py-1 px-2.5 rounded-md font-medium text-xs">
                        {Array.isArray(c.membersList) ? c.membersList.length : 0}
                      </span>
                    </TableCell>
                    <TableCell className="text-slate-600 px-4 py-3">
                      {c.deadline ? new Date(c.deadline).toLocaleDateString() : "-"}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-center">
                      <div className="flex justify-center items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => navigate(`/committees/${c._id || c.id}`)} className="h-8 w-8 p-0 text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition-colors" title="View Details">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => navigate(`/committees/edit/${c._id || c.id}`)} className="h-8 w-8 p-0 text-slate-600 hover:text-green-600 hover:bg-green-50 transition-colors" title="Edit Committee">
                          <Edit className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {current.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-10">No results</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </Card>
      </div>

      {renderPagination()}
    </div>
  );
};

export default CommitteeListTable;
