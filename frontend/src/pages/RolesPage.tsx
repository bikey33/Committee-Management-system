import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Shield, Plus, Pencil, Trash2, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { rolesService, Role, Permission } from "@/api/roles";

// ── Permission group labels ──────────────────────────────────────────────────
const GROUP_LABELS: Record<string, string> = {
  user_management: "User Management",
  settings: "System Settings",
  committee: "Committee Management",
  reports: "Reports & Analytics",
};

function groupPermissions(permissions: Permission[]): Record<string, Permission[]> {
  return permissions.reduce<Record<string, Permission[]>>((acc, p) => {
    const g = p.group || "other";
    if (!acc[g]) acc[g] = [];
    acc[g].push(p);
    return acc;
  }, {});
}

// ── Role Form Modal (create / edit name+description) ──────────────────────────
function RoleFormModal({
  open,
  onClose,
  role,
}: {
  open: boolean;
  onClose: () => void;
  role?: Role | null;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");

  const isEdit = !!role;

  const mutation = useMutation({
    mutationFn: () =>
      isEdit
        ? rolesService.update(role!.id, { name: name.trim(), description: description.trim() })
        : rolesService.create({ name: name.trim(), description: description.trim() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles"] });
      toast.success(isEdit ? "Role updated" : "Role created");
      onClose();
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.error || e.response?.data?.name?.[0] || "Failed to save role");
    },
  });

  // Reset form when modal opens
  const handleOpen = () => {
    setName(role?.name ?? "");
    setDescription(role?.description ?? "");
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose(); else handleOpen(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Role" : "New Role"}</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-4 py-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="role-name">Role Name</Label>
            <Input
              id="role-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Committee Secretary"
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="role-desc">Description</Label>
            <Textarea
              id="role-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional — describe what this role can do"
              rows={3}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!name.trim() || mutation.isPending}
          >
            {mutation.isPending ? "Saving…" : isEdit ? "Save" : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Permissions Modal ─────────────────────────────────────────────────────────
function PermissionsModal({
  open,
  onClose,
  role,
  allPermissions,
}: {
  open: boolean;
  onClose: () => void;
  role: Role;
  allPermissions: Permission[];
}) {
  const qc = useQueryClient();

  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(role.permissions.map((p) => p.codename))
  );

  const grouped = groupPermissions(allPermissions);

  const toggle = (codename: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(codename) ? next.delete(codename) : next.add(codename);
      return next;
    });
  };

  const toggleGroup = (group: string) => {
    const groupCodenames = grouped[group].map((p) => p.codename);
    const allChecked = groupCodenames.every((c) => selected.has(c));
    setSelected((prev) => {
      const next = new Set(prev);
      groupCodenames.forEach((c) => (allChecked ? next.delete(c) : next.add(c)));
      return next;
    });
  };

  const mutation = useMutation({
    mutationFn: () => rolesService.setPermissions(role.id, Array.from(selected)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles"] });
      toast.success(`Permissions saved for "${role.name}"`);
      onClose();
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.error || "Failed to save permissions");
    },
  });

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            Permissions — <span className="text-primary">{role.name}</span>
          </DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-5 max-h-[65vh] overflow-y-auto pr-1">
          {Object.entries(grouped).map(([group, perms]) => {
            const allChecked = perms.every((p) => selected.has(p.codename));
            const someChecked = perms.some((p) => selected.has(p.codename));
            const selectedCount = perms.filter((p) => selected.has(p.codename)).length;

            return (
              <div key={group}>
                {/* Group header */}
                <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-border/60">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      {GROUP_LABELS[group] ?? group}
                    </span>
                    <span className="text-[10px] text-muted-foreground/70">
                      {selectedCount}/{perms.length}
                    </span>
                  </div>
                  <label className="flex items-center gap-1.5 cursor-pointer select-none">
                    <span className="text-[11px] text-muted-foreground">Select all</span>
                    <Checkbox
                      checked={allChecked ? true : someChecked ? "indeterminate" : false}
                      onCheckedChange={() => toggleGroup(group)}
                      aria-label={`Toggle all ${GROUP_LABELS[group] ?? group}`}
                    />
                  </label>
                </div>

                {/* Permissions grid — 2 columns */}
                <div className="grid grid-cols-1 gap-px sm:grid-cols-2">
                  {perms.map((perm) => {
                    const checked = selected.has(perm.codename);
                    return (
                      <label
                        key={perm.codename}
                        className={cn(
                          "flex cursor-pointer items-start gap-2.5 rounded-md px-2.5 py-2 transition-colors hover:bg-accent/30",
                          checked && "bg-primary/5"
                        )}
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={() => toggle(perm.codename)}
                          className="mt-0.5 shrink-0"
                        />
                        <div className="min-w-0">
                          <p className="text-[11px] font-mono leading-tight text-foreground truncate">
                            {perm.codename}
                          </p>
                          <p className="text-[10px] text-muted-foreground leading-tight mt-0.5 truncate">
                            {perm.name}
                          </p>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        <DialogFooter>
          <span className="mr-auto text-xs text-muted-foreground">
            {selected.size} permission{selected.size !== 1 ? "s" : ""} selected
          </span>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Save Permissions"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export function RolesPage() {
  const qc = useQueryClient();

  const { data: roles = [], isLoading } = useQuery({
    queryKey: ["roles"],
    queryFn: rolesService.getAll,
  });

  const { data: allPermissions = [] } = useQuery({
    queryKey: ["allPermissions"],
    queryFn: rolesService.getAllPermissions,
  });

  const [formOpen, setFormOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [permRole, setPermRole] = useState<Role | null>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: number) => rolesService.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["roles"] });
      toast.success("Role deleted");
    },
    onError: (e: any) => {
      toast.error(e.response?.data?.error || "Cannot delete role — users may be assigned to it");
    },
  });

  const handleDelete = (role: Role) => {
    if (role.user_count > 0) {
      toast.error(`Cannot delete "${role.name}" — ${role.user_count} user(s) assigned`);
      return;
    }
    if (window.confirm(`Delete role "${role.name}"?`)) {
      deleteMutation.mutate(role.id);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            <Shield size={28} className="text-primary" />
            Roles & Permissions
          </h1>
          <p className="mt-1 text-muted-foreground">
            Manage roles and the permissions assigned to each
          </p>
        </div>
        <Button onClick={() => { setEditingRole(null); setFormOpen(true); }} className="flex items-center gap-2">
          <Plus size={16} />
          New Role
        </Button>
      </div>

      {/* Role Cards */}
      {isLoading ? (
        <div className="py-12 text-center text-muted-foreground">Loading roles…</div>
      ) : roles.length === 0 ? (
        <div className="py-12 text-center text-muted-foreground">No roles yet.</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {roles.map((role) => (
            <Card key={role.id} className="border-t-4 border-t-primary/60 shadow-sm">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base font-semibold leading-tight">
                    {role.name}
                  </CardTitle>
                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={() => { setEditingRole(role); setFormOpen(true); }}
                      className="text-muted-foreground hover:text-foreground transition-colors p-1"
                      title="Edit role"
                    >
                      <Pencil size={15} />
                    </button>
                    <button
                      onClick={() => handleDelete(role)}
                      disabled={deleteMutation.isPending}
                      className="text-muted-foreground hover:text-destructive transition-colors p-1"
                      title="Delete role"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>
                {role.description && (
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{role.description}</p>
                )}
              </CardHeader>

              <CardContent className="flex flex-col gap-3 pt-0">
                {/* User count */}
                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <Users size={13} />
                  <span>{role.user_count} user{role.user_count !== 1 ? "s" : ""}</span>
                </div>

                {/* Permission pills */}
                <div className="flex flex-wrap gap-1.5">
                  {role.permissions.length === 0 ? (
                    <span className="text-xs text-muted-foreground italic">No permissions</span>
                  ) : (
                    role.permissions.map((p) => (
                      <Badge
                        key={p.codename}
                        variant="secondary"
                        className="text-[10px] font-mono px-1.5 py-0"
                      >
                        {p.codename}
                      </Badge>
                    ))
                  )}
                </div>

                {/* Edit permissions button */}
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-1 w-full text-xs"
                  onClick={() => setPermRole(role)}
                >
                  <Shield size={13} className="mr-1.5" />
                  Edit Permissions
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Modals */}
      <RoleFormModal
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditingRole(null); }}
        role={editingRole}
      />

      {permRole && (
        <PermissionsModal
          open={!!permRole}
          onClose={() => setPermRole(null)}
          role={permRole}
          allPermissions={allPermissions}
        />
      )}
    </div>
  );
}
