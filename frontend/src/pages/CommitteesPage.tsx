import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Pencil, Trash2, Users } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { committeesService, Committee } from "@/api/committees";
import { CommitteeFormModal } from "@/components/committee/CommitteeFormModal";
import { CommitteeMembersModal } from "@/components/committee/CommitteeMembersModal";
import CommitteeDetailModal from "@/components/committee/CommitteeDetailModal";
import { toast } from "sonner";

export function CommitteesPage() {
  const queryClient = useQueryClient();
  
  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isMembersOpen, setIsMembersOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  
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
    if (window.confirm("Are you sure you want to delete this committee?")) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header Area */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">Committees</h1>
          <p className="text-muted-foreground mt-1">All committees across your offices</p>
        </div>
        <Button 
          onClick={handleCreateNew}
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground flex items-center justify-center gap-2 sm:w-auto"
        >
          <Plus size={16} />
          New Committee
        </Button>
      </div>

      {/* Table Area */}
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
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  Loading committees...
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-destructive">
                  Error loading committees. Please try again.
                </TableCell>
              </TableRow>
            ) : committees?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No committees found. Create one to get started.
                </TableCell>
              </TableRow>
            ) : (
              committees?.map((committee: Committee) => (
                <TableRow 
                  key={getCommitteeId(committee) || committee.name}
                  onClick={() => handleViewDetails(getCommitteeId(committee) || "")}
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                >
                  <TableCell className="font-medium text-foreground py-4">
                    {committee.name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="bg-background text-foreground border-border font-normal capitalize">
                      {committee.committee_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{committee.office_name || "N/A"}</TableCell>
                  <TableCell className="text-muted-foreground">{committee.members_count || 0}</TableCell>
                  <TableCell className="text-muted-foreground">{committee.formation_date || "Not set"}</TableCell>
                  <TableCell>
                    <Badge className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium border-transparent rounded-full px-3 capitalize">
                      {committee.committee_status || committee.status || "Active"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right pr-6" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center justify-end gap-3">
                      <button 
                        onClick={() => handleManageMembers(committee)}
                        className="text-muted-foreground hover:text-primary transition-colors"
                        title="Manage Members"
                      >
                        <Users size={18} />
                      </button>
                      <button 
                        onClick={() => handleEdit(committee)}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                        title="Edit Committee"
                      >
                        <Pencil size={18} />
                      </button>
                      <button 
                        onClick={() => handleDelete(getCommitteeId(committee) || "")}
                        disabled={deleteMutation.isPending}
                        className="text-destructive/80 hover:text-destructive transition-colors disabled:opacity-50"
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
      </div>

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
    </div>
  );
}
