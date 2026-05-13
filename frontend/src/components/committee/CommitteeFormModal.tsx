import React, { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { committeesService, Committee } from "@/api/committees";
import { officesService } from "@/api/offices";
import { usersService, User } from "@/api/users";
import { toast } from "sonner";
import { Search, X, Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const committeeSchema = z.object({
  name: z.string().min(1, "Name is required"),
  purpose: z.string().min(1, "Purpose is required"),
  committee_type: z.string().min(1, "Committee type is required"),
  deadline: z.string().optional().nullable(),
  formation_date: z.string().optional().nullable(),
  office: z.string().optional().nullable(),
});

type CommitteeFormValues = z.infer<typeof committeeSchema>;

interface Props {
  isOpen: boolean;
  onClose: () => void;
  committeeToEdit?: Committee | null;
}

export function CommitteeFormModal({ isOpen, onClose, committeeToEdit }: Props) {
  const queryClient = useQueryClient();
  const isEditing = !!committeeToEdit;

  // Form Hook
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CommitteeFormValues>({
    resolver: zodResolver(committeeSchema),
    defaultValues: {
      name: "",
      purpose: "",
      committee_type: "review",
      deadline: "",
      formation_date: "",
      office: "",
    },
  });

  const [formationLetter, setFormationLetter] = useState<File | null>(null);
  const currentOffice = watch("office");

  // Member Management State
  const [selectedMembers, setSelectedMembers] = useState<User[]>([]);
  const [memberSearch, setMemberSearch] = useState("");
  const [isMemberPopoverOpen, setIsMemberPopoverOpen] = useState(false);

  // External Data Fetching
  const { data: offices } = useQuery({
    queryKey: ["offices"],
    queryFn: officesService.getAll,
    enabled: isOpen,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: usersService.getAll,
    enabled: isOpen,
  });

  // Filter available users for dropdown
  const filteredUsers = users?.filter(user => {
    if (!memberSearch) return true;
    const searchLower = memberSearch.toLowerCase();
    const userName = user.name || "";
    const empId = user.employeeId || user.employee_id || user._id || "";
    const username = user.username || "";
    
    return (
      userName.toLowerCase().includes(searchLower) ||
      username.toLowerCase().includes(searchLower) ||
      empId.toLowerCase().includes(searchLower)
    );
  });

  // Restoration on Edit
  useEffect(() => {
    if (committeeToEdit && isOpen) {
      // Core info
      reset({
        name: committeeToEdit.name,
        purpose: committeeToEdit.purpose,
        committee_type: committeeToEdit.committee_type,
        deadline: committeeToEdit.deadline || "",
        formation_date: committeeToEdit.formation_date || "",
        office: committeeToEdit.office ? String(committeeToEdit.office) : "",
      });

      // Members
      if (committeeToEdit.membersList && users) {
        const restoredMembers = users.filter((u) => {
          const empId = u.employeeId || u.employee_id || u._id;
          return committeeToEdit.membersList?.some((m) => m.employeeId === empId);
        });
        setSelectedMembers(restoredMembers);
      } else {
         setSelectedMembers([]);
      }
      setFormationLetter(null);
    } else if (!isOpen) {
      reset();
      setSelectedMembers([]);
      setMemberSearch("");
      setFormationLetter(null);
    }
  }, [committeeToEdit, isOpen, reset, users]);

  // Re-sync members once users finish loading if we missed it in the first tick
  useEffect(() => {
      if (committeeToEdit && users && selectedMembers.length === 0 && (committeeToEdit.membersList?.length || 0) > 0) {
        const restoredMembers = users.filter((u) => {
          const empId = u.employeeId || u.employee_id || u._id;
          return committeeToEdit.membersList?.some((m) => m.employeeId === empId);
        });
        setSelectedMembers(restoredMembers);
      }
  }, [users, committeeToEdit]);


  const toggleMember = (user: any) => {
    setSelectedMembers((prev) => {
      const userEmpId = user.employeeId || user.employee_id || user._id;
      const exists = prev.find((u: any) => {
        const uEmpId = u.employeeId || u.employee_id || u._id;
        return uEmpId === userEmpId;
      });
      
      if (exists) {
        return prev.filter((u: any) => {
          const uEmpId = u.employeeId || u.employee_id || u._id;
          return uEmpId !== userEmpId;
        });
      }
      return [...prev, user];
    });
  };

  const mutation = useMutation({
    mutationFn: (data: any) => {
      const formData = new FormData();
      formData.append("name", data.name);
      formData.append("purpose", data.purpose);
      formData.append("committee_type", data.committee_type);
      if (data.deadline) formData.append("deadline", data.deadline);
      if (data.formation_date) formData.append("formation_date", data.formation_date);
      if (data.office) formData.append("office", data.office);
      
      // Members as JSON string for multipart/form-data
      const members = selectedMembers.map((m: any) => ({
        employeeId: m.employeeId || m.employee_id || m._id,
        role: "member",
      }));
      formData.append("members", JSON.stringify(members));

      if (formationLetter) {
        formData.append("formation_letter", formationLetter);
      }

      if (isEditing) {
        // Handle both 'id' and '_id' properties
        const committeeId = committeeToEdit?.id || committeeToEdit?._id;
        if (!committeeId) {
          throw new Error("Committee ID not found");
        }
        return committeesService.update(committeeId, formData);
      }
      return committeesService.create(formData);
    },
    onSuccess: (data: any) => {
      console.log("Committee update/create response:", data);
      // Invalidate both list and specific committee cache so detail views refresh
      queryClient.invalidateQueries({ queryKey: ["committees"] });
      const committeeId = committeeToEdit?.id || committeeToEdit?._id || (data?.data?.committee?.id || data?.data?.committee?._id || data?.committee?.id || data?.committee?._id);
      if (committeeId) {
        queryClient.invalidateQueries({ queryKey: ["committee", String(committeeId)] });
      }
      toast.success(`Committee ${isEditing ? "updated" : "created"} successfully`);
      onClose();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "An error occurred while saving.");
    },
  });

  const onSubmit = (data: CommitteeFormValues) => {
    mutation.mutate(data);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="h-[92vh] w-[95vw] max-w-[640px] overflow-y-auto sm:h-auto sm:max-h-[90vh] sm:w-[95vw]">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Committee" : "Create New Committee"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-2">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-2 md:col-span-1">
              <Label htmlFor="name">Committee Name</Label>
              <Input id="name" {...register("name")} placeholder="e.g. Specification Review" />
              {errors.name && <span className="text-sm text-red-500">{errors.name.message}</span>}
            </div>

            <div className="space-y-2 md:col-span-1">
              <Label htmlFor="office">Assigned Office</Label>
              <select
                id="office"
                value={currentOffice || ""}
                onChange={(e) => setValue("office", e.target.value)}
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="">-- Select Office --</option>
                {offices?.map((o: any) => (
                  <option key={o.id} value={o.id}>
                    {o.name} ({o.code})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="purpose">Description (Purpose)</Label>
            <Textarea id="purpose" {...register("purpose")} placeholder="Enter committee scope/purpose..." className="h-20" />
            {errors.purpose && <span className="text-sm text-red-500">{errors.purpose.message}</span>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="committee_type">Type</Label>
              <select
                id="committee_type"
                className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                {...register("committee_type")}
              >
                <option value="specification">Specification</option>
                <option value="evaluation">Evaluation</option>
                <option value="review">Review</option>
                <option value="contract">Contract</option>
                <option value="other">Other</option>
              </select>
              {errors.committee_type && <span className="text-sm text-red-500">{errors.committee_type.message}</span>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="deadline">Deadline</Label>
              <Input id="deadline" type="date" {...register("deadline")} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="formation_date">Formation Date</Label>
              <Input id="formation_date" type="date" {...register("formation_date")} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="formation_letter">Formation Letter (Optional)</Label>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
              <Input
                id="formation_letter"
                type="file"
                accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                onChange={(e) => setFormationLetter(e.target.files?.[0] || null)}
                className="cursor-pointer"
              />
              {isEditing && committeeToEdit?.formationLetterURL && !formationLetter && (
                <a
                  href={committeeToEdit.formationLetterURL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary hover:underline flex items-center gap-1 shrink-0"
                >
                  Current File
                </a>
              )}
            </div>
          </div>

          {/* Multi-Select Member logic */}
          <div className="space-y-2">
            <Label>Initial Members</Label>
            <div className="flex flex-wrap gap-2 min-h-[40px] rounded-md border border-input bg-muted/30 p-2">
              {selectedMembers.length === 0 && (
                <span className="text-sm text-muted-foreground p-1">No members selected yet.</span>
              )}
              {selectedMembers.map((member: any) => {
                const empId = member.employeeId || member.employee_id || member._id;
                return (
                <Badge key={empId} variant="secondary" className="flex gap-1 items-center pl-2 pr-1.5 py-1">
                  {member.name || member.first_name || member.username} ({empId})
                  <button
                    type="button"
                    onClick={() => toggleMember(member)}
                    className="ml-1 hover:bg-destructive hover:text-white rounded-full p-0.5"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              )})}
            </div>
            <Popover open={isMemberPopoverOpen} onOpenChange={setIsMemberPopoverOpen}>
              <PopoverTrigger asChild>
                <Button variant="outline" className="w-full justify-start text-muted-foreground mt-1">
                  <Search className="mr-2 h-4 w-4" />
                  Find & Add Users by Name or ID...
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[92vw] p-0 sm:w-[550px]" align="start">
                <div className="flex items-center border-b px-3">
                  <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                  <input
                    className="flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                    placeholder="Type name or employee ID..."
                    value={memberSearch}
                    onChange={(e) => setMemberSearch(e.target.value)}
                  />
                </div>
                <ScrollArea className="h-[250px]">
                  <div className="p-1">
                    {filteredUsers?.length === 0 ? (
                      <div className="text-center py-6 text-sm text-muted-foreground">No users found.</div>
                    ) : (
                      filteredUsers?.map((user: any) => {
                        const userEmpId = user.employeeId || user.employee_id || user._id;
                        const isSelected = !!selectedMembers.find((m: any) => {
                          const mEmpId = m.employeeId || m.employee_id || m._id;
                          return mEmpId === userEmpId;
                        });
                        return (
                          <div
                            key={userEmpId}
                            className="flex items-center px-2 py-2 cursor-pointer rounded hover:bg-accent hover:text-accent-foreground"
                            onClick={() => toggleMember(user)}
                          >
                            <div className={`flex h-4 w-4 mr-2 items-center justify-center border rounded-sm ${isSelected ? "bg-primary border-primary text-primary-foreground" : "border-primary"}`}>
                              {isSelected && <Check className="h-3 w-3" />}
                            </div>
                            <div className="flex flex-col">
                              <span className="font-medium text-sm">{user.name || user.first_name} {user.last_name ? user.last_name : ""} {user.username ? `(${user.username})` : ""}</span>
                              <span className="text-xs text-muted-foreground">ID: {userEmpId} | {user.office?.name || user.office_name || "No Office Assigned"}</span>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </ScrollArea>
              </PopoverContent>
            </Popover>
          </div>

          <DialogFooter className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending} className="w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto">
              {mutation.isPending ? "Saving..." : isEditing ? "Save Changes" : "Create Committee"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
