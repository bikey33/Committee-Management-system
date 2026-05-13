// CommitteeDetail.tsx
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Info } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetCommitteeById } from "@/hooks/useCommittees";
import CommitteeDetailContent from "./CommitteeDetailContent";

const CommitteeDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // Use the standard hook which handles auth headers and API endpoints correctly
  const { data: committeeData, isLoading: loading, error } = useGetCommitteeById(id);
  
  // The committee data is often nested in a .data.committee property depending on response shape
  // Let's normalize it to handle both direct and nested shapes
  const committeeRaw = (committeeData as any);
  const committee = committeeRaw?.data?.committee || committeeRaw?.committee || committeeRaw;

  if (loading) {
    return (
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        <Skeleton className="h-10 w-40" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-96 w-full" />
          </div>
          <div className="space-y-6">
            <Skeleton className="h-48 w-full" />
            <Skeleton className="h-48 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !committee) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="bg-red-50 p-4 rounded-full">
          <Info className="h-12 w-12 text-red-500" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900">Wait, something went wrong</h2>
        <p className="text-slate-500">{error?.message || "Committee details could not be loaded."}</p>
        <Button onClick={() => navigate("/committee")}>Back to Committees</Button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* Back Action */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate("/committee")}
          className="hover:bg-slate-100/80 rounded-full"
        >
          <ArrowLeft className="h-5 w-5 text-slate-600" />
        </Button>
      </div>

      <CommitteeDetailContent committee={committee} id={id || ""} />
    </div>
  );
};

export default CommitteeDetail;