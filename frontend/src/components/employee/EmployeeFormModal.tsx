import { useEffect } from "react";
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
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { employeesService, Employee } from "@/api/employees";
import { toast } from "sonner";

const employeeSchema = z.object({
  employee_id: z
    .string()
    .min(1, "Employee ID is required")
    .max(10, "Employee ID must be 10 characters or fewer"),
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Enter a valid email").or(z.literal("")),
  phone: z.string().optional(),
  department: z.string().optional(),
  designation: z.string().optional(),
  position: z.string().optional(),
  level: z.string().optional(),
});

type EmployeeFormValues = z.infer<typeof employeeSchema>;

interface Props {
  isOpen: boolean;
  onClose: () => void;
  employeeToEdit?: Employee | null;
}

export function EmployeeFormModal({ isOpen, onClose, employeeToEdit }: Props) {
  const queryClient = useQueryClient();
  const isEditing = !!employeeToEdit;

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EmployeeFormValues>({
    resolver: zodResolver(employeeSchema),
    defaultValues: {
      employee_id: "",
      name: "",
      email: "",
      phone: "",
      department: "",
      designation: "",
      position: "",
      level: "",
    },
  });

  useEffect(() => {
    if (employeeToEdit && isOpen) {
      reset({
        employee_id: employeeToEdit.employee_id,
        name: employeeToEdit.name || "",
        email: employeeToEdit.email || "",
        phone: employeeToEdit.phone || employeeToEdit.mno || "",
        department: employeeToEdit.department || "",
        designation: employeeToEdit.designation || "",
        position: employeeToEdit.position || "",
        level: employeeToEdit.level || "",
      });
    } else if (!isOpen) {
      reset();
    }
  }, [employeeToEdit, isOpen, reset]);

  const mutation = useMutation({
    mutationFn: (data: EmployeeFormValues) => {
      const payload: Partial<Employee> = {
        name: data.name,
        email: data.email || null,
        phone: data.phone || null,
        department: data.department || null,
        designation: data.designation || null,
        position: data.position || null,
        level: data.level || null,
      };
      if (isEditing) {
        return employeesService.update(employeeToEdit!.employee_id, payload);
      }
      return employeesService.create({ ...payload, employee_id: data.employee_id.trim() });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      // A new/edited employee may change who's available for user creation.
      queryClient.invalidateQueries({ queryKey: ["availableEmployees"] });
      toast.success(`Employee ${isEditing ? "updated" : "created"} successfully`);
      onClose();
    },
    onError: (error: any) => {
      const data = error.response?.data;
      const msg =
        data?.detail ||
        (data && typeof data === "object"
          ? Object.values(data).flat().join(", ")
          : null) ||
        "An error occurred while saving the employee";
      toast.error(msg);
    },
  });

  const onSubmit = (data: EmployeeFormValues) => mutation.mutate(data);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[90vh] w-[95vw] max-w-[560px] overflow-y-auto sm:w-full">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Employee" : "Create New Employee"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="employee_id">Employee ID</Label>
            <Input
              id="employee_id"
              {...register("employee_id")}
              placeholder="e.g. 1480"
              disabled={isEditing}
            />
            {isEditing && (
              <p className="text-xs text-muted-foreground">Employee ID cannot be changed.</p>
            )}
            {errors.employee_id && (
              <span className="text-sm text-destructive">{errors.employee_id.message}</span>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" {...register("name")} placeholder="Full name" />
            {errors.name && <span className="text-sm text-destructive">{errors.name.message}</span>}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" {...register("email")} placeholder="user@ntc.net.np" />
              {errors.email && <span className="text-sm text-destructive">{errors.email.message}</span>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Phone</Label>
              <Input id="phone" {...register("phone")} placeholder="98XXXXXXXX" />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="department">Department / Office</Label>
              <Input id="department" {...register("department")} placeholder="e.g. IT Directorate" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="designation">Designation</Label>
              <Input id="designation" {...register("designation")} placeholder="e.g. Engineer" />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="position">Position</Label>
              <Input id="position" {...register("position")} placeholder="e.g. Officer" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="level">Level</Label>
              <Input id="level" {...register("level")} placeholder="e.g. 7" />
            </div>
          </div>

          <DialogFooter className="flex flex-col-reverse gap-2 pt-4 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto"
            >
              {mutation.isPending ? "Saving..." : isEditing ? "Save Changes" : "Create Employee"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
