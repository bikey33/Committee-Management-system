import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { committeesService, Committee } from "@/api/committees";
import CommitteeListTable from "@/components/committee/CommitteeListTable";
import { CommitteeFormModal } from "@/components/committee/CommitteeFormModal";
import { CommitteeMembersModal } from "@/components/committee/CommitteeMembersModal";
import CommitteeDetailModal from "@/components/committee/CommitteeDetailModal";
import { PermissionGate } from "@/components/PermissionGate";
import { toast } from "sonner";

export function CommitteesPage() {
  const queryClient = useQueryClient();
  
  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isMembersOpen, setIsMembersOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [committeeToDelete, setCommitteeToDelete] = useState<Committee | null>(null);
  
  // Selected committee state
  const [selectedCommittee, setSelectedCommittee] = useState<Committee | null>(null);
  const [selectedCommitteeId, setSelectedCommitteeId] = useState<string | null>(null);

  const getCommitteeId = (committee: Committee) => {
    return committee.id || committee._id || null;
  };

  // Fetch committees
  const { data: committees, isLoading, isError } = useQuery({
    queryKey: ["committees"],
    queryFn: committeesService.getAll,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => committeesService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["committees"] });
      toast.success("Committee deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete committee");
    },
  });

  const handleCreateNew = () => {
    setSelectedCommittee(null);
    setIsFormOpen(true);
  };

  const handleEdit = (committee: Committee) => {
    setSelectedCommittee(committee);
    setIsFormOpen(true);
  };

  const handleManageMembers = (committee: Committee) => {
    setSelectedCommittee(committee);
    setIsMembersOpen(true);
  };

  const handleViewDetails = (committeeId: string) => {
    if (!committeeId) return;
    setSelectedCommitteeId(committeeId);
    setIsDetailOpen(true);
  };

  const handleDelete = (id: string) => {
    if (!id) return;
    deleteMutation.mutate(id, {
      onSettled: () => setCommitteeToDelete(null),
    });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header Area */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Committees</h1>
          <p className="text-muted-foreground mt-1">All committees across your offices</p>
        </div>
        <PermissionGate codename="committee.create">
          <Button
            onClick={handleCreateNew}
            className="w-full bg-primary hover:bg-primary/90 text-primary-foreground flex items-center justify-center gap-2 sm:w-auto"
          >
            <Plus size={16} />
            New Committee
          </Button>
        </PermissionGate>
      </div>

      {/* Table Area */}
      {isLoading ? (
        <div className="border rounded-xl bg-card p-8 text-center text-muted-foreground shadow-sm">
          Loading committees...
        </div>
      ) : isError ? (
        <div className="border rounded-xl bg-card p-8 text-center text-destructive shadow-sm">
          Error loading committees. Please try again.
        </div>
      ) : committees?.length === 0 ? (
        <div className="border rounded-xl bg-card p-8 text-center text-muted-foreground shadow-sm">
          No committees found. Create one to get started.
        </div>
      ) : (
        <CommitteeListTable
          committees={committees || []}
          onView={handleViewDetails}
          onEdit={handleEdit}
          onManageMembers={handleManageMembers}
          onDelete={(c) => setCommitteeToDelete(c)}
        />
      )}

      {/* Modals */}
      <CommitteeFormModal 
        isOpen={isFormOpen} 
        onClose={() => setIsFormOpen(false)} 
        committeeToEdit={selectedCommittee}
      />
      
      <CommitteeMembersModal
        isOpen={isMembersOpen}
        onClose={() => setIsMembersOpen(false)}
        committee={selectedCommittee}
      />

      <CommitteeDetailModal
        id={selectedCommitteeId}
        isOpen={isDetailOpen}
        onClose={() => {
          setIsDetailOpen(false);
          setSelectedCommitteeId(null);
        }}
      />

      <AlertDialog
        open={!!committeeToDelete}
        onOpenChange={(open) => {
          if (!open) {
            setCommitteeToDelete(null);
          }
        }}
      >
        <AlertDialogContent className="w-[95vw] max-w-md sm:w-full">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Committee</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this committee?
              <span className="mt-2 block text-foreground">
                This action cannot be undone.
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>No</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleDelete(getCommitteeId(committeeToDelete!) || "")}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Yes
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
