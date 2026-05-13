import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/hooks/use-toast';
import { committeeRolesApi, type CommitteeRoleAdmin } from '@/services/api/committee-roles';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Plus, Pencil, Trash2, Loader2 } from 'lucide-react';

const CommitteeRoleManager: React.FC = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editItem, setEditItem] = useState<CommitteeRoleAdmin | null>(null);
  const [deleteItem, setDeleteItem] = useState<CommitteeRoleAdmin | null>(null);

  // Form state
  const [formLabel, setFormLabel] = useState('');
  const [formValue, setFormValue] = useState('');
  const [formSortOrder, setFormSortOrder] = useState('0');

  const { data: roles = [], isLoading } = useQuery({
    queryKey: ['committee-roles-admin'],
    queryFn: committeeRolesApi.listAll,
  });

  const createMutation = useMutation({
    mutationFn: committeeRolesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['committee-roles-admin'] });
      queryClient.invalidateQueries({ queryKey: ['committee-roles'] });
      toast({ title: 'Role created successfully' });
      closeAddDialog();
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to create role',
        description: error?.response?.data?.error || error?.message || 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { label?: string; sort_order?: number; is_active?: boolean } }) =>
      committeeRolesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['committee-roles-admin'] });
      queryClient.invalidateQueries({ queryKey: ['committee-roles'] });
      toast({ title: 'Role updated successfully' });
      setEditItem(null);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to update role',
        description: error?.response?.data?.error || error?.message || 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: committeeRolesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['committee-roles-admin'] });
      queryClient.invalidateQueries({ queryKey: ['committee-roles'] });
      toast({ title: 'Role deleted successfully' });
      setDeleteItem(null);
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to delete role',
        description: error?.response?.data?.error || error?.message || 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      committeeRolesApi.update(id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['committee-roles-admin'] });
      queryClient.invalidateQueries({ queryKey: ['committee-roles'] });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to toggle role status',
        description: error?.response?.data?.error || error?.message,
        variant: 'destructive',
      });
    },
  });

  const closeAddDialog = () => {
    setIsAddOpen(false);
    setFormLabel('');
    setFormValue('');
    setFormSortOrder('0');
  };

  const openEditDialog = (item: CommitteeRoleAdmin) => {
    setEditItem(item);
    setFormLabel(item.label);
    setFormSortOrder(String(item.sort_order));
  };

  const handleCreate = () => {
    if (!formLabel.trim()) return;
    const value = formValue.trim() || formLabel.trim().toLowerCase().replace(/\s+/g, '_');
    createMutation.mutate({
      value,
      label: formLabel.trim(),
      sort_order: parseInt(formSortOrder) || 0,
      is_active: true,
    });
  };

  const handleUpdate = () => {
    if (!editItem || !formLabel.trim()) return;
    updateMutation.mutate({
      id: editItem.id,
      data: { label: formLabel.trim(), sort_order: parseInt(formSortOrder) || 0 },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-foreground">Committee Role Types</h3>
          <p className="text-sm text-muted-foreground">
            Manage the role types that can be assigned to committee members.
          </p>
        </div>
        <Button onClick={() => setIsAddOpen(true)} size="sm" className="w-full sm:w-auto">
          <Plus className="h-4 w-4 mr-1" /> Add Role
        </Button>
      </div>

      {roles.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">No committee roles configured yet.</p>
        </Card>
      ) : (
        <div className="border rounded-md overflow-hidden bg-white shadow-sm border-t-4 border-t-[hsl(209,100%,32%)]">
          <div className="w-full overflow-x-auto">
          <Table className="min-w-[760px]">
            <TableHeader className="bg-[hsl(209_100%_32%)]">
              <TableRow className="hover:bg-transparent border-b border-white/10">
                <TableHead className="font-bold text-white h-11 tracking-tight">Label</TableHead>
                <TableHead className="font-bold text-white h-11 tracking-tight">Value</TableHead>
                <TableHead className="font-bold text-white h-11 tracking-tight">Sort Order</TableHead>
                <TableHead className="font-bold text-white h-11 tracking-tight">Status</TableHead>
                <TableHead className="font-bold text-white h-11 w-[120px] tracking-tight">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {roles.map((role) => (
                <TableRow key={role.id}>
                  <TableCell className="font-medium">{role.label}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="font-mono text-xs">
                      {role.value}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{role.sort_order}</TableCell>
                  <TableCell>
                    <Switch
                      checked={role.is_active}
                      onCheckedChange={(checked) =>
                        toggleActiveMutation.mutate({ id: role.id, is_active: checked })
                      }
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="icon" onClick={() => openEditDialog(role)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => setDeleteItem(role)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        </div>
      )}

      {/* Add Role Dialog */}
      <Dialog open={isAddOpen} onOpenChange={(open) => !open && closeAddDialog()}>
        <DialogContent className="w-[95vw] max-w-lg sm:w-full">
          <DialogHeader>
            <DialogTitle>Add Committee Role</DialogTitle>
            <DialogDescription>Create a new role type for committee members.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="role-label">Label</Label>
              <Input
                id="role-label"
                value={formLabel}
                onChange={(e) => setFormLabel(e.target.value)}
                placeholder="e.g., Recorder"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role-value">Value (auto-generated if empty)</Label>
              <Input
                id="role-value"
                value={formValue}
                onChange={(e) => setFormValue(e.target.value)}
                placeholder="e.g., recorder"
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role-sort">Sort Order</Label>
              <Input
                id="role-sort"
                type="number"
                value={formSortOrder}
                onChange={(e) => setFormSortOrder(e.target.value)}
                placeholder="0"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeAddDialog}>Cancel</Button>
            <Button onClick={handleCreate} disabled={createMutation.isPending || !formLabel.trim()}>
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Role Dialog */}
      <Dialog open={!!editItem} onOpenChange={(open) => !open && setEditItem(null)}>
        <DialogContent className="w-[95vw] max-w-lg sm:w-full">
          <DialogHeader>
            <DialogTitle>Edit Role</DialogTitle>
            <DialogDescription>
              Update the role <span className="font-semibold">{editItem?.label}</span>
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-label">Label</Label>
              <Input
                id="edit-label"
                value={formLabel}
                onChange={(e) => setFormLabel(e.target.value)}
                placeholder="Role label"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-sort">Sort Order</Label>
              <Input
                id="edit-sort"
                type="number"
                value={formSortOrder}
                onChange={(e) => setFormSortOrder(e.target.value)}
                placeholder="0"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditItem(null)}>Cancel</Button>
            <Button onClick={handleUpdate} disabled={updateMutation.isPending || !formLabel.trim()}>
              {updateMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteItem} onOpenChange={(open) => !open && setDeleteItem(null)}>
        <AlertDialogContent className="w-[95vw] max-w-md sm:w-full">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Role</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the role <span className="font-semibold">{deleteItem?.label}</span>?
              Roles that are currently assigned to committee members cannot be deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteItem && deleteMutation.mutate(deleteItem.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default CommitteeRoleManager;
