import React, { useEffect } from "react";
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { officesService, Office } from "@/api/offices";
import { toast } from "sonner";

const officeSchema = z.object({
  name: z.string().min(1, "Name is required"),
  code: z.string().min(1, "Code is required"),
  department: z.string().optional().nullable(),
});

type OfficeFormValues = z.infer<typeof officeSchema>;

interface Props {
  isOpen: boolean;
  onClose: () => void;
  officeToEdit?: Office | null;
}

export function OfficeFormModal({ isOpen, onClose, officeToEdit }: Props) {
  const queryClient = useQueryClient();
  const isEditing = !!officeToEdit;

  const { data: departments = [] } = useQuery({
    queryKey: ["departments"],
    queryFn: officesService.getDepartments,
    enabled: isOpen,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<OfficeFormValues>({
    resolver: zodResolver(officeSchema),
    defaultValues: {
      name: "",
      code: "",
      department: "",
    },
  });

  useEffect(() => {
    if (officeToEdit && isOpen) {
      reset({
        name: officeToEdit.name,
        code: officeToEdit.code,
        department: officeToEdit.department ? String(officeToEdit.department) : "",
      });
    } else if (!isOpen) {
      reset();
    }
  }, [officeToEdit, isOpen, reset]);

  const mutation = useMutation({
    mutationFn: (data: OfficeFormValues) => {
      const payload: Partial<Office> = {
        name: data.name,
        code: data.code,
        department: data.department ? parseInt(data.department) : null,
      };

      if (isEditing) {
        return officesService.update(officeToEdit.id, payload);
      }
      return officesService.create(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offices"] });
      toast.success(`Office ${isEditing ? "updated" : "created"} successfully`);
      onClose();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "An error occurred");
    },
  });

  const onSubmit = (data: OfficeFormValues) => {
    mutation.mutate(data);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-[95vw] max-w-[500px] sm:w-full">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Office" : "Create New Office"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="name">Office Name</Label>
            <Input id="name" {...register("name")} placeholder="e.g. IT Department" />
            {errors.name && <span className="text-sm text-destructive">{errors.name.message}</span>}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="code">Office Code</Label>
            <Input id="code" {...register("code")} placeholder="e.g. ITD" />
            {errors.code && <span className="text-sm text-destructive">{errors.code.message}</span>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="department">Department</Label>
            <select
              id="department"
              className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              {...register("department")}
            >
              <option value="">-- Select Department --</option>
              {departments?.map((department: any) => (
                <option key={department.id} value={department.id}>
                  {department.name} ({department.code})
                </option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">
              Select the single department this office belongs to.
            </p>
          </div>

          <DialogFooter className="flex flex-col-reverse gap-2 pt-4 sm:flex-row sm:justify-end">
            <Button type="button" variant="outline" onClick={onClose} className="w-full sm:w-auto">
              Cancel
            </Button>
            <Button type="submit" disabled={mutation.isPending} className="w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto">
              {mutation.isPending ? "Saving..." : isEditing ? "Save Changes" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
