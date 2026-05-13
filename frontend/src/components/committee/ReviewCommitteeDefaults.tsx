import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Users,
  UserPlus,
  Trash2,
  Loader2,
  X,
  Building2,
  Check,
  ChevronsUpDown,
  Mail,
  Phone,
  CreditCard,
  User,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { getRoleConfig } from "@/config/committeeRoleConfig";
import { cn } from "@/lib/utils";
import { useOffices } from "@/hooks/useOfficesQuery";
import { useGetReviewDefaults } from "@/hooks/useCommittees";
import { committeeApi } from "@/services/api/committee";
import EmployeeSearch from "@/components/committee/wizard/EmployeeSearch";
import type { Employee } from "@/types/employee";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { usePermissions } from "@/hooks/usePermissions";

const ROLES = [
  { value: "coordinator", label: "Coordinator" },
  { value: "secretary", label: "Secretary" },
  { value: "member", label: "Member" },
  { value: "invitee", label: "Invitee" },
  { value: "subject_expert", label: "Subject Expert" },
];



const ReviewCommitteeDefaults: React.FC = () => {
  const { user } = useAuth();
  const { isSuperAdmin } = usePermissions();
  const userOfficeId = user?.office?.id || (user as any)?.working_office?.id;
  
  const [selectedHierarchy, setSelectedHierarchy] = useState<string>(
    userOfficeId ? String(userOfficeId) : ""
  );
  const hierarchyParam = selectedHierarchy;
  const { data: defaults = [], isLoading } = useGetReviewDefaults({ roleHierarchyId: hierarchyParam });
  const { data: offices = [], isLoading: officesLoading } = useOffices();
  
  const filteredOffices = isSuperAdmin() 
    ? offices 
    : offices.filter(o => o.id === userOfficeId);

  const queryClient = useQueryClient();
  const [selectedEmployee, setSelectedEmployee] = useState<Employee | null>(null);
  const [selectedRole, setSelectedRole] = useState("member");
  const [isAdding, setIsAdding] = useState(false);
  const [removingId, setRemovingId] = useState<number | null>(null);
  const [open, setOpen] = useState(false);

  const existingIds = defaults.map((d: any) => d.employeeId);
  const hasCoordinator = defaults.some((d: any) => d.committee_role === "coordinator");
  const hasSecretary = defaults.some((d: any) => d.committee_role === "secretary");

  const selectedHierarchyLabel = selectedHierarchy === ""
    ? "Select Office"
    : filteredOffices.find((n) => String(n.id) === selectedHierarchy)?.name || selectedHierarchy;

  const handleAdd = async () => {
    if (!selectedEmployee) return;
    const employeeId = selectedEmployee.employee_id || selectedEmployee.employeeId;
    if (!employeeId) {
      toast.error("Employee ID not found");
      return;
    }
    if (selectedRole === "coordinator" && hasCoordinator) {
      toast.error("Only one Coordinator allowed per hierarchy level");
      return;
    }
    if (selectedRole === "secretary" && hasSecretary) {
      toast.error("Only one Secretary allowed per hierarchy level");
      return;
    }
    if (!selectedHierarchy) {
      toast.error("Please select an office first");
      return;
    }
    setIsAdding(true);
    try {
      await committeeApi.addReviewDefault({
        employeeId,
        committeeRole: selectedRole,
        roleHierarchyId: selectedHierarchy,
      });
      toast.success("Default member added");
      setSelectedEmployee(null);
      queryClient.invalidateQueries({ queryKey: ["review-committee-defaults"] });
    } catch (err: any) {
      toast.error(err?.details?.data?.error || err.message || "Failed to add default member");
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemove = async (id: number) => {
    setRemovingId(id);
    try {
      await committeeApi.removeReviewDefault(id);
      toast.success("Default member removed");
      queryClient.invalidateQueries({ queryKey: ["review-committee-defaults"] });
    } catch (err: any) {
      toast.error(err?.details?.data?.error || err.message || "Failed to remove");
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-foreground">Review Committee Default Members</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Configure default members per office/hierarchy level. Members are automatically added to new review committees for that level.
        </p>
      </div>

      {/* Hierarchy selector */}
      <Card className="overflow-hidden border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm">
        <CardHeader className="pb-3 border-b border-slate-50">
          <CardTitle className="text-sm font-bold flex items-center gap-2 text-[hsl(209,100%,32%)] tracking-tight">
            <Building2 className="w-4 h-4" />
            Office / Hierarchy Level
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="w-full justify-between"
              >
                {selectedHierarchyLabel}
                <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[92vw] p-0 min-w-0 sm:w-[var(--radix-popover-trigger-width)] sm:min-w-[300px]">
              <Command>
                <CommandInput placeholder="Search offices..." />
                <CommandList className="max-h-[300px] overflow-y-auto">
                  <CommandEmpty>No office found.</CommandEmpty>
                  <CommandGroup>
                    {officesLoading ? null : (
                      filteredOffices.map((office) => (
                        <CommandItem
                          key={office.id}
                          value={`${office.id} ${office.code || ''} ${office.name}`}
                          onSelect={() => {
                            setSelectedHierarchy(String(office.id));
                            setOpen(false);
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              selectedHierarchy === String(office.id) ? "opacity-100" : "opacity-0"
                            )}
                          />
                          {office.code ? `${office.code} - ` : ''}{office.name}
                        </CommandItem>
                      ))
                    )}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
          <p className="text-xs text-muted-foreground mt-2">
            {selectedHierarchy === ""
              ? "Select an office to view or configure its default members."
              : `Showing defaults for ${selectedHierarchyLabel}.`}
          </p>
        </CardContent>
      </Card>

      {selectedHierarchy !== "" && (
        <div className="space-y-6">
          {/* Add default member */}
          <Card className="overflow-hidden border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-50">
              <CardTitle className="text-sm font-bold flex items-center gap-2 text-[hsl(209,100%,32%)] tracking-tight">
                <UserPlus className="w-4 h-4" />
                Add Default Member to "{selectedHierarchyLabel}"
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <EmployeeSearch
                onSelectEmployee={setSelectedEmployee}
                excludeIds={existingIds}
              />

              {selectedEmployee && (
                <div className="flex flex-col gap-3 rounded-lg border bg-muted/30 p-3 sm:flex-row sm:items-center">
                  <span className="text-sm flex-1">
                    Adding: <strong>{selectedEmployee.name}</strong>
                    <span className="text-muted-foreground ml-1 text-xs">
                      ({selectedEmployee.employee_id || selectedEmployee.employeeId})
                    </span>
                  </span>
                  <Select value={selectedRole} onValueChange={setSelectedRole}>
                    <SelectTrigger className="w-full sm:w-[280px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROLES.map((r) => {
                        const isTaken =
                          (r.value === "coordinator" && hasCoordinator) ||
                          (r.value === "secretary" && hasSecretary);
                        return (
                          <SelectItem key={r.value} value={r.value} disabled={isTaken}>
                            {r.label}{isTaken ? " (already assigned)" : ""}
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                  <Button size="sm" onClick={handleAdd} disabled={isAdding} className="w-full sm:w-auto">
                    {isAdding ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4 mr-1" />}
                    Add
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setSelectedEmployee(null)} className="w-full sm:w-auto">
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Current defaults */}
          <Card className="overflow-hidden border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm">
            <CardHeader className="pb-3 border-b border-slate-50">
              <CardTitle className="text-sm font-bold flex items-center gap-2 text-[hsl(209,100%,32%)] tracking-tight">
                <Users className="w-4 h-4" />
                Current Defaults for "{selectedHierarchyLabel}" ({defaults.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : defaults.length > 0 ? (
                  <div className="space-y-2">
                  {defaults.map((member: any) => (
                    <Card key={member.id} className="border-slate-100 shadow-sm hover:shadow-md transition-shadow">
                      <CardContent className="flex flex-col gap-4 p-4 sm:flex-row sm:items-start">
                        <div className="flex-shrink-0">
                          <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center border border-blue-100 text-blue-600">
                            <User className="w-5 h-5" />
                          </div>
                        </div>

                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-[13px] text-slate-900 truncate tracking-tight">
                              {member.name}
                            </p>
                            <Badge
                              className={cn(
                                "text-[10px] font-bold py-0.5 px-2.5 rounded-full border-none shadow-sm",
                                getRoleConfig(member.committee_role).badgeClasses
                              )}
                            >
                              {getRoleConfig(member.committee_role).label}
                            </Badge>
                          </div>

                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
                            <div className="flex items-center gap-1.5">
                              <CreditCard className="h-3 w-3 text-slate-400" />
                              <span className="font-medium text-slate-600">{member.employeeId || member.employee_id}</span>
                            </div>
                            {member.email && (
                              <div className="flex items-center gap-1.5">
                                <Mail className="h-3 w-3 text-slate-400" />
                                <span className="font-medium text-slate-600">{member.email}</span>
                              </div>
                            )}
                            {member.phone && (
                              <div className="flex items-center gap-1.5">
                                <Phone className="h-3 w-3 text-slate-400" />
                                <span className="font-medium text-slate-600">{member.phone}</span>
                              </div>
                            )}
                          </div>

                        </div>

                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemove(member.id)}
                          disabled={removingId === member.id}
                          className="self-start text-slate-400 hover:text-destructive hover:bg-destructive/5 sm:self-auto"
                        >
                          {removingId === member.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No default members configured for "{selectedHierarchyLabel}". Add employees above to auto-include them in review committees.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ReviewCommitteeDefaults;
