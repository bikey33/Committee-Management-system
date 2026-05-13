import { useState, useEffect } from "react";
import { format } from "date-fns";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { useDepartments } from "@/hooks/useDepartments";
import { Committee } from "@/types/committee";
import { useAuth } from "@/contexts/AuthContext";
import SearchFilters from "./SearchFilters";
import { LoadingSpinner } from "@/components/common/LoadingSpinner";
import ErrorState from "./ErrorState";
import ResultsSummary from "./ResultsSummary";
import CommitteeCard from "./CommitteeCard";
import EmptyState from "@/components/common/EmptyState";
import CommitteePagination from "./CommitteePagination";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Eye, Calendar, FileCheck, ClipboardList, Users } from "lucide-react";

interface CommitteeSearchProps {
  committees: Committee[];
  loading: boolean;
  error: string | null;
  onCommitteesUpdate: (committees: Committee[]) => void;
  onCommitteeClick?: (committee: Committee) => void;
}

const ITEMS_PER_PAGE = 10;

const CommitteeSearch = ({
  committees = [],
  loading,
  error,
  onCommitteesUpdate,
  onCommitteeClick,
}: CommitteeSearchProps) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [formationDateFilter, setFormationDateFilter] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const navigate = useNavigate();
  const { toast } = useToast();
  const { token, user, hasPermission } = useAuth();

  const [officeFilter, setOfficeFilter] = useState<string>("all");
  const [planFilter, setPlanFilter] = useState<string>("all");

  const canViewAllInit = user?.user_role?.name.toLowerCase().includes("super admin") || (user?.user_role?.permissions?.includes('manage_all'));

  const renderDateWithSuperscript = (dateString: string | null | undefined) => {
    if (!dateString) return "-";
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

  // Load user's office as default selection
  useEffect(() => {
    // Try to match by code or name
    if (!canViewAllInit) {
      const defaultOffice = user?.office?.code || user?.office?.name;
      if (defaultOffice) {
        setOfficeFilter(defaultOffice);
      }
    }
  }, [user, canViewAllInit]);

  // Helper to safely get a committee ID from different shapes
  const getCommitteeId = (committee: Committee | any): string => {
    const rawId = committee?._id ?? committee?.id;
    if (!rawId) return "";
    if (typeof rawId === "object") {
      return (rawId as any).$oid ? String((rawId as any).$oid) : String(JSON.stringify(rawId));
    }
    return String(rawId);
  };

  const handleCommitteeClick = (committee: Committee) => {
    if (onCommitteeClick) {
      onCommitteeClick(committee);
    } else {
      const rawId = committee._id || (committee as any).id;
      const id = typeof rawId === "object" ? (rawId?.$oid ? String(rawId.$oid) : JSON.stringify(rawId)) : String(rawId || "");
      if (id) {
        navigate(`/committees/${id}`);
      }
    }
  };

  const handleClearFilters = () => {
    setSearchTerm("");
    setStatusFilter("all");
    setFormationDateFilter("");
    setTypeFilter("all");
    setOfficeFilter(user?.office?.code || "all");
    setPlanFilter("all");
    setCurrentPage(1);
  };



  const filteredCommittees = committees.filter((committee) => {
    // Restrict view to committees where user is creator, member, or from same office (unless super admin)
    const isSuperAdmin = user?.user_role?.name.toLowerCase().includes("super admin");
    const isCreator = committee.createdBy?.employeeId === user?.employee_id;
    const isMember = Array.isArray(committee.membersList) && 
                    committee.membersList.some(m => m.employeeId === user?.employee_id);
    const isSameOffice = (user?.office?.code && committee.office_code === user.office.code) || 
                        (user?.office?.name && committee.office_name === user.office.name);
    
    if (!isSuperAdmin && !isCreator && !isMember && !isSameOffice) {
      return false;
    }

    const matchesSearch =
      (committee.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (committee.purpose || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (committee.committee_type || "").toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === "all" ||
      (committee.approvalStatus ? committee.approvalStatus === statusFilter : (committee as any).approval_status === statusFilter);

    const matchesType = typeFilter === "all" || committee.committee_type === typeFilter;

    const matchesDate = !formationDateFilter || (committee.formation_date && committee.formation_date.startsWith(formationDateFilter));

    const matchesOffice = officeFilter === "all" || 
                         committee.office_code === officeFilter || 
                         committee.office_name === officeFilter;
    
    const matchesPlan = planFilter === "all" || committee.procurement_plan_name === planFilter;

    return matchesSearch && matchesStatus && matchesType && matchesDate && matchesOffice && matchesPlan;
  });

  // Calculate pagination
  const totalCount = filteredCommittees.length;
  const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE);
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, totalCount);
  const paginatedCommittees = filteredCommittees.slice(startIndex, endIndex);

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, statusFilter, formationDateFilter, typeFilter, officeFilter, planFilter]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" text="Loading Committee Management..." />
      </div>
    );
  }

  if (error) {
    return <ErrorState error={error} />;
  }

  const renderPagination = () => {
    if (!totalCount) return null;

    return (
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 py-0 px-2 mt-2 mb-4">
        {/* Left: Entries Info */}
        <div className="text-xs text-slate-500 whitespace-nowrap min-w-[200px]">
          Showing <span className="font-semibold text-slate-700">{startIndex + 1}</span> to{" "}
          <span className="font-semibold text-slate-700">{endIndex}</span> of{" "}
          <span className="font-semibold text-slate-700">{totalCount}</span> entries
        </div>

        {/* Center: Spacer */}
        <div className="flex-1 flex justify-center">
        </div>

        {/* Right: Navigation */}
        <div className="flex items-center gap-1 min-w-[300px] justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1 || loading}
            className="h-8 px-3 text-slate-400 border-slate-200 hover:bg-slate-50 hover:text-primary rounded font-medium text-xs bg-white shadow-sm"
          >
            « Prev
          </Button>

          <div className="flex items-center gap-1">
            {(() => {
              const pages = [];
              const maxVisible = 5;

              let startPage = Math.max(1, currentPage - 2);
              let endPage = Math.min(totalPages, startPage + maxVisible - 1);

              if (endPage - startPage < maxVisible - 1) {
                startPage = Math.max(1, endPage - maxVisible + 1);
              }

              for (let i = startPage; i <= endPage; i++) {
                pages.push(
                  <Button
                    key={i}
                    variant={currentPage === i ? "default" : "outline"}
                    size="sm"
                    onClick={() => handlePageChange(i)}
                    disabled={loading}
                    className={`h-8 w-8 p-0 font-bold transition-all duration-200 rounded text-xs ${currentPage === i
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
            onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages || loading}
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
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: "Specification", type: "specification", icon: Users, color: "text-[hsl(209,100%,32%)]", bg: "bg-blue-50", border: "border-t-[hsl(209,100%,32%)]" },
          { label: "Review", type: "review", icon: Eye, color: "text-[#E6B646]", bg: "bg-amber-50", border: "border-t-[#E6B646]" },
          { label: "Evaluation", type: "evaluation", icon: FileCheck, color: "text-[hsl(209,100%,32%)]", bg: "bg-blue-50", border: "border-t-[hsl(209,100%,32%)]" },
          { label: "Contract Preparation", type: "contract", icon: ClipboardList, color: "text-[#E6B646]", bg: "bg-amber-50", border: "border-t-[#E6B646]" },
        ].map((card) => {
          const count = filteredCommittees.filter(c => c.committee_type === card.type).length;
          return (
            <Card key={card.label} className={`p-4 border-slate-200 shadow-sm hover:shadow-md transition-shadow border-t-4 ${card.border}`}>
              <div className="flex items-center gap-4">
                <div className={`${card.bg} p-2.5 rounded-lg`}>
                  <card.icon className={`h-5 w-5 ${card.color}`} />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500">{card.label}</p>
                  <p className="text-2xl font-bold text-slate-900">{count}</p>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      <SearchFilters
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        formationDateFilter={formationDateFilter}
        setFormationDateFilter={setFormationDateFilter}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        typeFilter={typeFilter}
        setTypeFilter={setTypeFilter}
        officeFilter={officeFilter}
        setOfficeFilter={setOfficeFilter}
        planFilter={planFilter}
        setPlanFilter={setPlanFilter}
        committees={committees}
        user={user}
        canViewAllOffices={user?.user_role?.name.toLowerCase().includes("super admin") || hasPermission('manage_all')}
        filteredCount={filteredCommittees.length}
      />

      {/* Global Expandable Table Section */}
      {renderPagination()}
      <div className="relative -mt-4">

        {/* Replace card grid with a beautiful responsive table */}
        <Card className="bg-white border rounded-md shadow-sm overflow-hidden mt-4">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-[hsl(209_100%_32%)] border-b-0 [&_tr:first-child]:rounded-t-lg">
                <TableRow className="hover:bg-transparent border-0 text-white first:rounded-t-lg overflow-hidden">
                  <TableHead className="font-medium text-white px-4 first:rounded-tl-lg w-[60px]">SN</TableHead>
                  <TableHead className="font-medium text-white px-4">Office Code</TableHead>
                  <TableHead className="font-medium text-white px-4">Procurement Plan</TableHead>
                  <TableHead className="font-medium text-white px-4">Committee Name</TableHead>
                  <TableHead className="font-medium text-white px-4">Type</TableHead>
                  <TableHead className="text-center font-medium text-white px-4">Members</TableHead>
                  <TableHead className="font-medium text-white px-4">Formation</TableHead>
                  <TableHead className="text-center font-medium text-white px-4">Status</TableHead>
                  <TableHead className="text-center font-medium text-white px-4 last:rounded-tr-lg">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedCommittees.map((committee, index) => (
                  <TableRow key={getCommitteeId(committee)} className="hover:bg-muted/50 transition-colors duration-200 group border-b border-slate-100 last:border-0 text-sm">
                    <TableCell className="px-4 py-3 text-slate-600 font-medium">
                      {(currentPage - 1) * ITEMS_PER_PAGE + index + 1}
                    </TableCell>
                    <TableCell className="text-slate-600 px-4 py-3 whitespace-normal break-words">
                      {committee.office_code || committee.office_name || "-"}
                    </TableCell>
                    <TableCell className="text-slate-600 px-4 py-3 whitespace-normal break-words">
                      {committee.procurement_plan_name || "-"}
                    </TableCell>
                    <TableCell className="font-medium text-slate-900 px-4 py-3 cursor-pointer hover:underline whitespace-normal break-words" onClick={() => handleCommitteeClick(committee)}>
                      {committee.name || "-"}
                    </TableCell>
                    <TableCell className="capitalize text-slate-600 px-4 py-3">{committee.committee_type || "-"}</TableCell>
                    <TableCell className="text-center px-4 py-3">
                      <span className="bg-slate-100 text-slate-700 py-1 px-2.5 rounded-md font-medium text-xs">
                        {Array.isArray(committee.membersList) ? committee.membersList.length : 0}
                      </span>
                    </TableCell>
                    <TableCell className="text-slate-600 px-4 py-3 whitespace-nowrap">
                      {renderDateWithSuperscript(committee.formation_date)}
                    </TableCell>
                    <TableCell className="text-center px-4 py-3 capitalize text-slate-600">
                      {committee.approvalStatus || (committee as any).approval_status || "active"}
                    </TableCell>
                    <TableCell className="px-4 py-3 text-center">
                      <div className="flex justify-center items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleCommitteeClick(committee)} className="h-8 w-8 p-0 text-slate-600 hover:text-blue-600 hover:bg-blue-50 transition-colors" title="View Details">
                          <Eye className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {paginatedCommittees.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} className="p-0">
                      <EmptyState
                        title="No committees found"
                        description="Try adjusting your filters to discover more committees that match your criteria."
                        icon={Users}
                        hasFilters={!!(searchTerm || statusFilter !== "all" || formationDateFilter || typeFilter !== "all" || officeFilter !== "all" || planFilter !== "all")}
                        onClearFilters={() => {
                          setSearchTerm("");
                          setStatusFilter("all");
                          setFormationDateFilter("");
                          setTypeFilter("all");
                          setOfficeFilter(user?.office?.code || user?.office?.name || "all");
                          setPlanFilter("all");
                          setCurrentPage(1);
                        }}
                      />
                    </TableCell>
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

export default CommitteeSearch;
