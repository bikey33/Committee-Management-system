import React from "react";
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
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usersService } from "@/api/users";
import { toast } from "sonner";

const userSchema = z.object({
  employee_id: z.string().min(1, "Employee is required"),
  role_id: z.string().min(1, "Role assignment is required"),
});

type UserFormValues = z.infer<typeof userSchema>;

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function UserFormModal({ isOpen, onClose }: Props) {
  const queryClient = useQueryClient();

  const { data: availableEmployees, isLoading: loadingEmployees } = useQuery({
    queryKey: ["availableEmployees"],
    queryFn: usersService.getAvailableEmployees,
    enabled: isOpen,
  });

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: usersService.getRoles,
    enabled: isOpen,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<UserFormValues>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      employee_id: "",
      role_id: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: UserFormValues) => {
      return usersService.createFromEmployee({
        employee_id: data.employee_id,
        role_id: Number(data.role_id),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["availableEmployees"] });
      toast.success("User created successfully");
      reset();
      onClose();
    },
    onError: (error: any) => {
      // Handle nested DRF validation response messages elegantly
      const serverMsg = error.response?.data?.errors
        ? Object.values(error.response.data.errors).flat().join(", ")
        : error.response?.data?.detail;
      toast.error(serverMsg || "An error occurred while saving");
    },
  });

  const onSubmit = (data: UserFormValues) => {
    mutation.mutate(data);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-[95vw] max-w-[500px] sm:w-full">
        <DialogHeader>
          <DialogTitle>Register New User</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="employee_id">Select Employee</Label>
            <select
              id="employee_id"
              className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              {...register("employee_id")}
              disabled={loadingEmployees}
            >
              <option value="">-- Choose an unpromoted employee --</option>
              {availableEmployees?.map((emp: any) => (
                <option key={emp.employee_id} value={emp.employee_id}>
                  {emp.mapped_name || emp.name} ({emp.employee_id})
                </option>
              ))}
            </select>
            {errors.employee_id && <span className="text-sm text-destructive">{errors.employee_id.message}</span>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="role_id">System Role</Label>
            <select
              id="role_id"
              className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              {...register("role_id")}
            >
              <option value="">-- Select Access Level --</option>
              {roles?.map((role: any) => (
                <option key={role.id} value={role.id}>
                  {role.name}
                </option>
              ))}
            </select>
            {errors.role_id && <span className="text-sm text-destructive">{errors.role_id.message}</span>}
          </div>

          <DialogFooter className="flex flex-col-reverse gap-2 border-t pt-4 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending} className="w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto">
              {mutation.isPending ? "Creating..." : "Create System User"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
