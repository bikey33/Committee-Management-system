import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Trash2, UserPlus } from "lucide-react";
import { committeesService, Committee } from "@/api/committees";
import { toast } from "sonner";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  committee: Committee | null;
}

export function CommitteeMembersModal({ isOpen, onClose, committee }: Props) {
  const queryClient = useQueryClient();
  const [employeeId, setEmployeeId] = useState("");
  const [role, setRole] = useState("member");

  // Assuming getById returns memberships as well. If not, we might need a separate endpoint.
  // For now, let's assume `committee.memberships` comes from the detailed view.
  const { data: committeeDetails, isLoading } = useQuery({
    queryKey: ["committee", committee?.id],
    queryFn: () => committeesService.getById(committee!.id),
    enabled: !!committee?.id && isOpen,
  });

  const addMemberMutation = useMutation({
    mutationFn: (memberData: any) => committeesService.addMember(committee!.id, memberData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["committee", committee?.id] });
      queryClient.invalidateQueries({ queryKey: ["committees"] });
      toast.success("Member added successfully");
      setEmployeeId("");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to add member");
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (empId: string) => committeesService.removeMember(committee!.id, empId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["committee", committee?.id] });
      queryClient.invalidateQueries({ queryKey: ["committees"] });
      toast.success("Member removed successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to remove member");
    },
  });

  const handleAddMember = (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId) return;
    // memberData usually requires employee_id and committee_role
    addMemberMutation.mutate({ employee_id: employeeId, committee_role: role });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex h-[92vh] w-[95vw] max-w-[640px] flex-col sm:h-auto sm:max-h-[80vh] sm:w-[95vw]">
        <DialogHeader>
          <DialogTitle>Manage Members - {committee?.name}</DialogTitle>
        </DialogHeader>
        
        <div className="border-b border-border py-4">
          <form onSubmit={handleAddMember} className="flex flex-col gap-2 sm:flex-row">
            <Input 
              placeholder="Enter Employee ID" 
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              className="flex-1"
            />
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring sm:w-[150px]"
            >
              <option value="member">Member</option>
              <option value="chairperson">Chairperson</option>
              <option value="secretary">Secretary</option>
            </select>
            <Button type="submit" disabled={!employeeId || addMemberMutation.isPending} className="w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto">
              <UserPlus size={16} className="mr-2" /> Add
            </Button>
          </form>
        </div>

        <div className="flex-1 overflow-y-auto py-4">
          <h4 className="text-sm font-medium text-muted-foreground mb-3">Current Members</h4>
          {isLoading ? (
            <p className="text-sm text-center text-muted-foreground py-4">Loading members...</p>
          ) : committeeDetails?.memberships?.length === 0 ? (
            <p className="text-sm text-center text-muted-foreground py-4">No members assigned yet.</p>
          ) : (
            <div className="space-y-2">
              {committeeDetails?.memberships?.map((membership: any, idx: number) => (
                <div key={idx} className="flex flex-col gap-3 rounded-lg border border-border bg-slate-50 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-medium text-foreground">{membership.user?.username || membership.employee_id}</p>
                    <p className="text-xs text-muted-foreground capitalize">{membership.committee_role}</p>
                  </div>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    className="self-end text-destructive/80 hover:text-destructive hover:bg-destructive/10 sm:self-auto"
                    onClick={() => removeMemberMutation.mutate(membership.user?.employee_id || membership.employee_id)}
                    disabled={removeMemberMutation.isPending}
                  >
                    <Trash2 size={16} />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
