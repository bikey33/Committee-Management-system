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
  employee_id: z.string().min(1, "Employee ID is required"),
  username: z.string().min(1, "Username is required"),
  email: z.string().email("Invalid email address"),
  role_id: z.string().min(1, "Role assignment is required"),
  password: z.string().optional(),
});

type UserFormValues = z.infer<typeof userSchema>;

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function UserFormModal({ isOpen, onClose }: Props) {
  const queryClient = useQueryClient();

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
      username: "",
      email: "",
      role_id: "",
      password: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (data: UserFormValues) => {
      // If password not provided, generate a random temporary password
      const password = data.password && data.password.length > 0 ? data.password : Math.random().toString(36).slice(-10) + "A1!";
      return usersService.register({
        employee_id: data.employee_id,
        username: data.username,
        email: data.email,
        password,
        role: Number(data.role_id),
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
            <Label htmlFor="employee_id">Employee ID</Label>
            <input
              id="employee_id"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              {...register("employee_id")}
            />
            {errors.employee_id && <span className="text-sm text-destructive">{errors.employee_id.message}</span>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <input
              id="username"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              {...register("username")}
            />
            {errors.username && <span className="text-sm text-destructive">{errors.username.message}</span>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <input
              id="email"
              type="email"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              {...register("email")}
            />
            {errors.email && <span className="text-sm text-destructive">{errors.email.message}</span>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password (optional)</Label>
            <input
              id="password"
              type="password"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              {...register("password")}
            />
            {errors.password && <span className="text-sm text-destructive">{errors.password.message}</span>}
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
