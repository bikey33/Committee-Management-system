import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Info, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useGetCommitteeById } from "@/hooks/useCommittees";
import CommitteeDetailContent from "./CommitteeDetailContent";
import { useEffect } from "react";

interface CommitteeDetailModalProps {
  id: string | null;
  isOpen: boolean;
  onClose: () => void;
}

const CommitteeDetailModal = ({ id, isOpen, onClose }: CommitteeDetailModalProps) => {
  const { data: committeeData, isLoading: loading, error } = useGetCommitteeById(id || undefined);
  
  // Log the data for debugging
  console.log('CommitteeDetailModal - data:', committeeData);
  console.log('CommitteeDetailModal - error:', error);
  console.log('CommitteeDetailModal - id:', id);
  
  const committeeRaw = committeeData as any;
  const committee = committeeRaw?.data?.committee || committeeRaw?.committee || committeeRaw?.data || committeeRaw;
  
  // Validate that committee has necessary data
  const isValidCommittee = committee && (committee.id || committee._id || committee.name);
  
  console.log('CommitteeDetailModal - extracted committee:', committee);
  console.log('CommitteeDetailModal - isValidCommittee:', isValidCommittee);

  // Extract error message from axios error
  const getErrorMessage = () => {
    if (!error) return null;
    
    const axiosError = error as any;
    const responseData = axiosError?.response?.data;
    
    if (typeof responseData === 'object') {
      return (
        responseData?.message ||
        responseData?.error ||
        responseData?.detail ||
        responseData?.non_field_errors?.[0] ||
        'Committee details could not be loaded. Please check your connection and try again.'
      );
    }
    
    return axiosError?.message || 'Committee details could not be loaded. Please check your connection and try again.';
  };

  // Expose close function to the content component if needed
  useEffect(() => {
    (window as any).closeModal = onClose;
    return () => {
      delete (window as any).closeModal;
    };
  }, [onClose]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="h-[92vh] w-[95vw] max-w-5xl border-0 p-0 shadow-2xl rounded-2xl flex flex-col overflow-hidden bg-white sm:h-auto sm:max-h-[90vh] sm:w-[95vw]">
        <DialogHeader className="sr-only">
          <DialogTitle>Committee Details</DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 flex flex-col overflow-hidden">
          {loading ? (
            <div className="p-4 space-y-6 flex-1 sm:p-8">
              <Skeleton className="h-10 w-2/3" />
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-6">
                  <Skeleton className="h-64 w-full" />
                  <Skeleton className="h-96 w-full" />
                </div>
                <div className="space-y-6">
                  <Skeleton className="h-48 w-full" />
                </div>
              </div>
            </div>
          ) : error || !isValidCommittee ? (
            <div className="flex flex-col items-center justify-center flex-1 space-y-4 p-4 sm:p-8">
              <div className="bg-red-50 p-4 rounded-full">
                <Info className="h-12 w-12 text-red-500" />
              </div>
              <h2 className="text-xl font-bold text-slate-900 text-center">Wait, something went wrong</h2>
              <p className="text-slate-500 text-center max-w-sm">{getErrorMessage()}</p>
              <Button onClick={onClose} variant="outline" className="font-bold">Close Window</Button>
            </div>
          ) : (
            <CommitteeDetailContent committee={committee} id={id || ""} />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CommitteeDetailModal;
