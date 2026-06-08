import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Plus, Pencil, Trash2, Building2 } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { officesService, Office } from "@/api/offices";
import { OfficeFormModal } from "@/components/office/OfficeFormModal";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Loader2 } from "lucide-react";
import { TablePagination } from "@/components/common/TablePagination";

const PAGE_SIZE = 10;

export function OfficesPage() {
  const queryClient = useQueryClient();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedOffice, setSelectedOffice] = useState<Office | null>(null);
  const [directorateName, setDirectorateName] = useState("");
  const [directorateDescription, setDirectorateDescription] = useState("");
  const [page, setPage] = useState(1);

  const { data: offices, isLoading, isError } = useQuery({
    queryKey: ["offices"],
    queryFn: officesService.getAll,
  });

  const totalItems = offices?.length ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  // Clamp page if the list shrank (e.g. after a delete).
  const currentPage = Math.min(page, totalPages);
  const pagedOffices: Office[] | undefined = offices?.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const { data: directorates = [], isLoading: directoratesLoading } = useQuery({
    queryKey: ["directorates"],
    queryFn: officesService.getDirectorates,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => officesService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["offices"] });
      toast.success("Office deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete office");
    },
  });

  const createDirectorateMutation = useMutation({
    mutationFn: (data: { name: string; description: string }) => officesService.createDirectorate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["directorates"] });
      queryClient.invalidateQueries({ queryKey: ["offices"] });
      toast.success("Directorate created successfully");
      setDirectorateName("");
      setDirectorateDescription("");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.error || "Failed to create directorate");
    },
  });

  const deleteDirectorateMutation = useMutation({
    mutationFn: (id: number) => officesService.deleteDirectorate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["directorates"] });
      queryClient.invalidateQueries({ queryKey: ["offices"] });
      toast.success("Directorate deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || error.response?.data?.error || "Failed to delete directorate");
    },
  });

  const handleCreateNew = () => {
    setSelectedOffice(null);
    setIsFormOpen(true);
  };

  const handleEdit = (office: Office) => {
    setSelectedOffice(office);
    setIsFormOpen(true);
  };

  const handleDelete = (id: number) => {
    if (window.confirm("Are you sure you want to delete this office?")) {
      deleteMutation.mutate(id);
    }
  };

  const formatDirectorate = (office: Office) => {
    return office.directorate_details?.name || office.directorate_name || "None";
  };

  const handleCreateDirectorate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!directorateName.trim()) return;
    createDirectorateMutation.mutate({
      name: directorateName.trim(),
      description: directorateDescription.trim(),
    });
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header Area */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            <Building2 size={28} className="text-primary" />
            Offices
          </h1>
          <p className="text-muted-foreground mt-1">Manage organizational offices and directorates</p>
        </div>
        <Button 
          onClick={handleCreateNew}
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground flex items-center justify-center gap-2 sm:w-auto"
        >
          <Plus size={16} />
          New Office
        </Button>
      </div>

      <Card className="overflow-hidden border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm">
        <CardHeader className="border-b border-slate-50 pb-3">
          <CardTitle className="text-sm font-bold tracking-tight text-[hsl(209,100%,32%)]">Directorates</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <form onSubmit={handleCreateDirectorate} className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Input value={directorateName} onChange={(e) => setDirectorateName(e.target.value)} placeholder="Directorate name" />
            <Button type="submit" disabled={createDirectorateMutation.isPending || !directorateName.trim()} className="w-full">
              {createDirectorateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4 mr-1" />}
              Add Directorate
            </Button>
            <Textarea
              value={directorateDescription}
              onChange={(e) => setDirectorateDescription(e.target.value)}
              placeholder="Optional description"
              className="md:col-span-3 min-h-[90px]"
            />
          </form>

          <div className="space-y-2">
            {directoratesLoading ? (
              <div className="flex items-center justify-center py-6 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : directorates.length > 0 ? (
              directorates.map((directorate: any) => (
                <div key={directorate.id} className="flex flex-col gap-3 rounded-lg border border-slate-100 bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-medium text-slate-900">{directorate.name}</p>
                      <Badge className="bg-slate-100 text-slate-700 hover:bg-slate-100">{directorate.office_count || 0} offices</Badge>
                    </div>
                    {directorate.description ? <p className="mt-1 text-sm text-slate-500">{directorate.description}</p> : null}
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    className="self-start text-destructive hover:text-destructive hover:bg-destructive/5 sm:self-auto"
                    disabled={deleteDirectorateMutation.isPending}
                    onClick={() => deleteDirectorateMutation.mutate(directorate.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))
            ) : (
              <p className="py-4 text-center text-sm text-muted-foreground">No directorates yet.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Table Area */}
      <div className="border rounded-xl bg-card shadow-sm overflow-hidden">
        <div className="w-full overflow-x-auto">
        <Table className="min-w-[760px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[300px]">Office Name</TableHead>
              <TableHead>Code</TableHead>
              <TableHead>Directorate</TableHead>
              <TableHead className="text-right pr-6">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                  Loading offices...
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-destructive">
                  Error loading offices. Please try again.
                </TableCell>
              </TableRow>
            ) : offices?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                  No offices found. Create one to get started.
                </TableCell>
              </TableRow>
            ) : (
              pagedOffices?.map((office: Office) => (
                <TableRow key={office.id}>
                  <TableCell className="font-medium text-foreground py-4">
                    {office.name}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="bg-background text-foreground border-border font-normal">
                      {office.code}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDirectorate(office)}
                  </TableCell>
                  <TableCell className="text-right pr-6">
                    <div className="flex items-center justify-end gap-3">
                      <button 
                        onClick={() => handleEdit(office)}
                        className="text-muted-foreground hover:text-foreground transition-colors"
                        title="Edit Office"
                      >
                        <Pencil size={18} />
                      </button>
                      <button 
                        onClick={() => handleDelete(office.id)}
                        disabled={deleteMutation.isPending}
                        className="text-destructive/80 hover:text-destructive transition-colors disabled:opacity-50"
                        title="Delete Office"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        </div>
        {!isLoading && !isError && totalItems > 0 && (
          <TablePagination
            page={currentPage}
            totalPages={totalPages}
            onPageChange={setPage}
            totalItems={totalItems}
            pageSize={PAGE_SIZE}
          />
        )}
      </div>

      <OfficeFormModal
        isOpen={isFormOpen} 
        onClose={() => setIsFormOpen(false)} 
        officeToEdit={selectedOffice}
      />
    </div>
  );
}
