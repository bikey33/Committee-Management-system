
import { Star } from "lucide-react";

interface ResultsSummaryProps {
  searchTerm: string;
  statusFilter: string;
  departmentFilter: string;
  typeFilter: string;
  filteredCount: number;
  totalCount: number;
}

const ResultsSummary = ({
  searchTerm,
  statusFilter,
  departmentFilter,
  typeFilter,
  filteredCount,
  totalCount,
}: ResultsSummaryProps) => {
  const hasActiveFilters = searchTerm || statusFilter !== "all" || departmentFilter !== "all" || typeFilter !== "all";

  if (!hasActiveFilters) return null;

  return (
    <div className="relative bg-gradient-to-r from-blue-50/90 via-indigo-50/80 to-purple-50/90 backdrop-blur-xl rounded-2xl border border-blue-200/50 p-6 shadow-xl overflow-hidden">
      <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-blue-400/10 to-purple-500/10 rounded-full blur-2xl"></div>
      <div className="relative flex items-center gap-4">
        <div className="p-3 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl shadow-lg">
          <Star className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-blue-800 font-bold text-lg">
            Found {filteredCount} of {totalCount} committees
            {searchTerm && <span className="ml-2 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">matching "{searchTerm}"</span>}
          </p>
          <p className="text-blue-600 text-sm mt-1">Active filters are being applied</p>
        </div>
      </div>
    </div>
  );
};

export default ResultsSummary;
