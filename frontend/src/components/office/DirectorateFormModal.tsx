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
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { officesService } from "@/api/offices";
import { toast } from "sonner";

const directorateSchema = z.object({
  name: z.string().min(1, "Directorate name is required"),
  description: z.string().optional(),
});

type DirectorateFormValues = z.infer<typeof directorateSchema>;

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function DirectorateFormModal({ isOpen, onClose }: Props) {
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DirectorateFormValues>({
    resolver: zodResolver(directorateSchema),
    defaultValues: { name: "", description: "" },
  });

  useEffect(() => {
    if (!isOpen) reset();
  }, [isOpen, reset]);

  const mutation = useMutation({
    mutationFn: (data: DirectorateFormValues) =>
      officesService.createDirectorate({
        name: data.name.trim(),
        description: (data.description || "").trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["directorates"] });
      queryClient.invalidateQueries({ queryKey: ["offices"] });
      toast.success("Directorate created successfully");
      onClose();
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail ||
          error.response?.data?.error ||
          "Failed to create directorate"
      );
    },
  });

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-[95vw] max-w-[480px] sm:w-full">
        <DialogHeader>
          <DialogTitle>Add Directorate</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="dir-name">Directorate Name</Label>
            <Input
              id="dir-name"
              {...register("name")}
              placeholder="e.g. Information Technology Directorate"
            />
            {errors.name && (
              <span className="text-sm text-destructive">{errors.name.message}</span>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="dir-desc">Description</Label>
            <Textarea
              id="dir-desc"
              {...register("description")}
              placeholder="Optional description"
              className="min-h-[90px]"
            />
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
              {mutation.isPending ? "Saving..." : "Create Directorate"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
