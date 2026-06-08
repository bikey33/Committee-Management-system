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
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersService, User as UserModel } from "@/api/users";
import { toast } from "sonner";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  user: UserModel | null;
}

const inputClass =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

export function UserEditModal({ isOpen, onClose, user }: Props) {
  const queryClient = useQueryClient();

  const [name, setName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [roleId, setRoleId] = React.useState("");
  const [isActive, setIsActive] = React.useState(true);

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: usersService.getRoles,
    enabled: isOpen,
  });

  // Populate the form from the selected user whenever the modal opens.
  React.useEffect(() => {
    if (isOpen && user) {
      setName(user.name || `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim());
      setEmail(user.email || "");
      const currentRole = user.user_role_details?.id ?? user.user_role?.id;
      setRoleId(currentRole != null ? String(currentRole) : "");
      setIsActive(user.isActive ?? user.is_active ?? true);
    }
  }, [isOpen, user]);

  const employeeId = user?.employeeId || user?.employee_id || "";

  const mutation = useMutation({
    mutationFn: () =>
      usersService.update(employeeId, {
        name: name.trim(),
        email: email.trim(),
        isActive,
        ...(roleId ? { user_role_id: Number(roleId) } : {}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("User updated successfully");
      onClose();
    },
    onError: (error: any) => {
      const serverMsg = error.response?.data?.message
        ? typeof error.response.data.message === "string"
          ? error.response.data.message
          : Object.values(error.response.data.message).flat().join(", ")
        : error.response?.data?.detail;
      toast.error(serverMsg || "An error occurred while updating the user");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeId) {
      toast.error("Missing employee ID");
      return;
    }
    mutation.mutate();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-[95vw] max-w-[500px] sm:w-full">
        <DialogHeader>
          <DialogTitle>Edit User</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="edit-employee-id">Employee ID</Label>
            <Input id="edit-employee-id" value={employeeId} disabled />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-name">Name</Label>
            <Input
              id="edit-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-email">Email</Label>
            <Input
              id="edit-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-role">System Role</Label>
            <select
              id="edit-role"
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

          <div className="flex items-center justify-between rounded-md border p-3">
            <div>
              <Label htmlFor="edit-active">Active</Label>
              <p className="text-sm text-muted-foreground">
                Inactive users cannot log in.
              </p>
            </div>
            <Switch id="edit-active" checked={isActive} onCheckedChange={setIsActive} />
          </div>

          <DialogFooter className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="w-full sm:w-auto"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto"
            >
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
