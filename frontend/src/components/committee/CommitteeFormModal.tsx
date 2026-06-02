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
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

const fallbackRoleOptions = [
  { id: 1, value: "coordinator", label: "Coordinator" },
  { id: 2, value: "secretary", label: "Secretary" },
  { id: 3, value: "member", label: "Member" },
];

const getEmployeeId = (user: any) => user.employeeId || user.employee_id || user._id || "";

const formatDateInput = (date: Date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const parseDeadlineDays = (deadlineDays: string) => {
  const parsed = Number.parseInt(deadlineDays, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
};

const calculateDeadlineDate = (formationDate: string, deadlineDays: string) => {
  if (!formationDate) return "";
  const parsedDeadlineDays = parseDeadlineDays(deadlineDays);
  if (!parsedDeadlineDays) return "";

  const date = new Date(`${formationDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return "";

  date.setDate(date.getDate() + parsedDeadlineDays);
  return formatDateInput(date);
};

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
  const [deadlineDays, setDeadlineDays] = useState("30");

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
  const formationDate = watch("formation_date") || "";
  const computedDeadline = calculateDeadlineDate(formationDate, deadlineDays);

  // Member Management State
  const [selectedMembers, setSelectedMembers] = useState<User[]>([]);
  const [memberRoles, setMemberRoles] = useState<Record<string, string>>({});
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

  const { data: roleOptions = fallbackRoleOptions } = useQuery({
    queryKey: ["committee-roles"],
    queryFn: async () => {
      const response = await committeesService.getRoles();
      const roles = Array.isArray(response?.data) ? response.data : [];
      if (!roles.length) return fallbackRoleOptions;
      return roles;
    },
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
      const restoredFormationDate = committeeToEdit.formation_date || "";
      const restoredDeadline = committeeToEdit.deadline || "";
      const formationDateObject = restoredFormationDate ? new Date(`${restoredFormationDate}T00:00:00`) : null;
      const deadlineDateObject = restoredDeadline ? new Date(`${restoredDeadline}T00:00:00`) : null;
      const restoredDeadlineDays =
        formationDateObject && deadlineDateObject
          ? Math.max(1, Math.round((deadlineDateObject.getTime() - formationDateObject.getTime()) / (1000 * 60 * 60 * 24)))
          : 30;

      setDeadlineDays(String(restoredDeadlineDays));

      // Core info
      reset({
        name: committeeToEdit.name,
        purpose: committeeToEdit.purpose,
        committee_type: committeeToEdit.committee_type,
        deadline: restoredDeadline,
        formation_date: restoredFormationDate,
        office: committeeToEdit.office ? String(committeeToEdit.office) : "",
      });

      // Members
      if (committeeToEdit.membersList && users) {
        const restoredMembers = users.filter((u) => {
          const empId = getEmployeeId(u);
          return committeeToEdit.membersList?.some((m) => m.employeeId === empId);
        });
        setSelectedMembers(restoredMembers);

        const restoredRoles: Record<string, string> = {};
        committeeToEdit.membersList.forEach((m) => {
          restoredRoles[m.employeeId] = (m.role || "member").toLowerCase();
        });
        setMemberRoles(restoredRoles);
      } else {
         setSelectedMembers([]);
         setMemberRoles({});
      }
      setFormationLetter(null);
    } else if (!isOpen) {
      reset();
      setDeadlineDays("30");
      setSelectedMembers([]);
      setMemberRoles({});
      setMemberSearch("");
      setFormationLetter(null);
    }
  }, [committeeToEdit, isOpen, reset, users]);

  // Re-sync members once users finish loading if we missed it in the first tick
  useEffect(() => {
      if (committeeToEdit && users && selectedMembers.length === 0 && (committeeToEdit.membersList?.length || 0) > 0) {
        const restoredMembers = users.filter((u) => {
          const empId = getEmployeeId(u);
          return committeeToEdit.membersList?.some((m) => m.employeeId === empId);
        });
        setSelectedMembers(restoredMembers);

        const restoredRoles: Record<string, string> = {};
        committeeToEdit.membersList?.forEach((m) => {
          restoredRoles[m.employeeId] = (m.role || "member").toLowerCase();
        });
        setMemberRoles(restoredRoles);
      }
  }, [users, committeeToEdit]);


  useEffect(() => {
    setMemberRoles((prev) => {
      const next: Record<string, string> = {};
      selectedMembers.forEach((member: any) => {
        const empId = getEmployeeId(member);
        if (empId) {
          next[empId] = prev[empId] || "member";
        }
      });
      return next;
    });
  }, [selectedMembers]);


  const toggleMember = (user: any) => {
    const userEmpId = getEmployeeId(user);

    setSelectedMembers((prev) => {
      const exists = prev.find((u: any) => {
        const uEmpId = getEmployeeId(u);
        return uEmpId === userEmpId;
      });
      
      if (exists) {
        setMemberRoles((previousRoles) => {
          const updatedRoles = { ...previousRoles };
          delete updatedRoles[userEmpId];
          return updatedRoles;
        });
        return prev.filter((u: any) => {
          const uEmpId = getEmployeeId(u);
          return uEmpId !== userEmpId;
        });
      }

      setMemberRoles((previousRoles) => ({
        ...previousRoles,
        [userEmpId]: previousRoles[userEmpId] || "member",
      }));
      return [...prev, user];
    });
  };

  const handleRoleChange = (employeeId: string, role: string) => {
    setMemberRoles((prev) => ({ ...prev, [employeeId]: role }));
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
        employeeId: getEmployeeId(m),
        role: memberRoles[getEmployeeId(m)] || "member",
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
    const roleCounts = selectedMembers.reduce(
      (acc, member: any) => {
        const empId = getEmployeeId(member);
        const role = (memberRoles[empId] || "member").toLowerCase();
        if (role === "coordinator") acc.coordinator += 1;
        if (role === "secretary") acc.secretary += 1;
        return acc;
      },
      { coordinator: 0, secretary: 0 }
    );

    if (selectedMembers.length === 0) {
      toast.error("Please add committee members before submitting.");
      return;
    }

    if (roleCounts.coordinator !== 1) {
      toast.error("Please assign exactly one coordinator.");
      return;
    }

    if (roleCounts.secretary !== 1) {
      toast.error("Please assign exactly one secretary.");
      return;
    }

    mutation.mutate({
      ...data,
      deadline: calculateDeadlineDate(data.formation_date || "", deadlineDays),
    });
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

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
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
              <Label htmlFor="formation_date">Formation Date</Label>
              <Input id="formation_date" type="date" {...register("formation_date")} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="deadline_days">Deadline Days</Label>
              <Input
                id="deadline_days"
                type="number"
                min="1"
                step="1"
                value={deadlineDays}
                onChange={(e) => setDeadlineDays(e.target.value)}
                placeholder="Enter deadline days"
              />
            </div>

            <div className="space-y-2 md:col-span-3">
              <Label htmlFor="deadline_preview">Deadline Date</Label>
              <Input id="deadline_preview" type="date" value={computedDeadline} readOnly />
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
            <div className="space-y-2 min-h-[40px] rounded-md border border-input bg-muted/30 p-2">
              {selectedMembers.length === 0 && (
                <span className="text-sm text-muted-foreground p-1">No members selected yet.</span>
              )}
              {selectedMembers.map((member: any) => {
                const empId = getEmployeeId(member);
                return (
                <div key={empId} className="flex flex-col gap-2 rounded-md border bg-background p-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="text-sm">
                    <span className="font-medium">{member.name || member.first_name || member.username}</span> ({empId})
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={memberRoles[empId] || "member"}
                      onChange={(e) => handleRoleChange(empId, e.target.value)}
                      className="h-9 rounded-md border border-input bg-background px-2 py-1 text-sm"
                    >
                      {roleOptions.map((role: any) => (
                        <option key={role.id || role.value} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => toggleMember(member)}
                      className="hover:bg-destructive hover:text-white rounded-full p-1"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
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
