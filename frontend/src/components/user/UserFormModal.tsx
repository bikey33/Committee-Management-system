import React from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersService } from "@/api/users";
import { toast } from "sonner";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

interface AvailableEmployee {
  employee_id: string;
  name?: string;
  email?: string;
  phone?: string;
  mapped_phone?: string;
  mapped_name?: string;
  position?: string;
  department?: string;
}

const inputClass =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

export function UserFormModal({ isOpen, onClose }: Props) {
  const queryClient = useQueryClient();

  const [selectedId, setSelectedId] = React.useState("");
  const [roleId, setRoleId] = React.useState("");
  const [employeeOpen, setEmployeeOpen] = React.useState(false);

  const { data: employees = [], isLoading: employeesLoading } = useQuery<AvailableEmployee[]>({
    queryKey: ["availableEmployees"],
    queryFn: usersService.getAvailableEmployees,
    enabled: isOpen,
  });

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: usersService.getRoles,
    enabled: isOpen,
  });

  // Preselect the default "Member" role once roles load.
  React.useEffect(() => {
    if (!roleId && Array.isArray(roles)) {
      const member = roles.find((r: any) => r.name === "Member");
      if (member) setRoleId(String(member.id));
    }
  }, [roles, roleId]);

  const resetForm = () => {
    setSelectedId("");
    setRoleId("");
    setEmployeeOpen(false);
  };

  const selected = employees.find((e) => e.employee_id === selectedId);
  const selectedPhone = selected?.mapped_phone || selected?.phone || "";

  const mutation = useMutation({
    mutationFn: (data: { employee_id: string; role_id: number }) =>
      usersService.createFromEmployee(data),
    onSuccess: (res: any) => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["availableEmployees"] });
      const generated = res?.data?.generated_password;
      if (generated) {
        toast.success(
          `User created. No phone on file — temporary password: ${generated}`,
          { duration: 15000 }
        );
      } else {
        toast.success("User created. They can log in with OTP sent to their registered phone.");
      }
      resetForm();
      onClose();
    },
    onError: (error: any) => {
      const serverMsg = error.response?.data?.errors
        ? Object.values(error.response.data.errors).flat().join(", ")
        : error.response?.data?.detail || error.response?.data?.message;
      toast.error(serverMsg || "An error occurred while creating the user");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId) {
      toast.error("Please select an employee");
      return;
    }
    if (!roleId) {
      toast.error("Please select a role");
      return;
    }
    mutation.mutate({ employee_id: selectedId, role_id: Number(roleId) });
  };

  return (
    <Dialog
      open={isOpen}
      onOpenChange={(open) => {
        if (!open) {
          resetForm();
          onClose();
        }
      }}
    >
      <DialogContent className="w-[95vw] max-w-[500px] sm:w-full">
        <DialogHeader>
          <DialogTitle>Create User from Employee</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="employee">Employee</Label>
            <Popover open={employeeOpen} onOpenChange={setEmployeeOpen}>
              <PopoverTrigger asChild>
                <button
                  id="employee"
                  type="button"
                  role="combobox"
                  aria-expanded={employeeOpen}
                  disabled={employeesLoading}
                  className={cn(inputClass, "items-center justify-between gap-2 text-left")}
                >
                  <span className={cn("truncate", !selected && "text-muted-foreground")}>
                    {employeesLoading
                      ? "Loading employees..."
                      : selected
                      ? `${selected.name || "Unnamed"} (${selected.employee_id})`
                      : "-- Select an employee --"}
                  </span>
                  <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
                </button>
              </PopoverTrigger>
              <PopoverContent
                className="w-[--radix-popover-trigger-width] p-0"
                align="start"
              >
                <Command>
                  <CommandInput placeholder="Search by name, employee ID or email" />
                  <CommandList>
                    <CommandEmpty>No employee found.</CommandEmpty>
                    <CommandGroup>
                      {employees.map((emp) => (
                        <CommandItem
                          key={emp.employee_id}
                          value={`${emp.name || "Unnamed"} ${emp.employee_id} ${emp.email || ""}`}
                          onSelect={() => {
                            setSelectedId(
                              emp.employee_id === selectedId ? "" : emp.employee_id
                            );
                            setEmployeeOpen(false);
                          }}
                        >
                          <Check
                            className={cn(
                              "mr-2 h-4 w-4",
                              selectedId === emp.employee_id ? "opacity-100" : "opacity-0"
                            )}
                          />
                          <span className="truncate">
                            {(emp.name || "Unnamed")} ({emp.employee_id})
                          </span>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {selected && (
            <div className="space-y-1 rounded-md border bg-muted/40 p-3 text-sm">
              <div><span className="text-muted-foreground">Email:</span> {selected.email || "—"}</div>
              <div><span className="text-muted-foreground">Phone:</span> {selectedPhone || "—"}</div>
              {!selectedPhone && (
                <div className="text-destructive">
                  No phone on file — a temporary password will be generated instead of OTP login.
                </div>
              )}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="role_id">System Role</Label>
            <select
              id="role_id"
              className={inputClass}
              value={roleId}
              onChange={(e) => setRoleId(e.target.value)}
            >
              <option value="">-- Select Access Level --</option>
              {Array.isArray(roles) &&
                roles.map((role: any) => (
                  <option key={role.id} value={role.id}>
                    {role.name}
                  </option>
                ))}
            </select>
          </div>

          <DialogFooter className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                resetForm();
                onClose();
              }}
              className="w-full sm:w-auto"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto"
            >
              {mutation.isPending ? "Creating..." : "Create User"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
