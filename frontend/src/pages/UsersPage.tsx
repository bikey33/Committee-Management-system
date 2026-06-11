import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Plus, User, Pencil, Trash2 } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { usersService, User as UserModel } from "@/api/users";
import { UserFormModal } from "@/components/user/UserFormModal";
import { UserEditModal } from "@/components/user/UserEditModal";
import { UserProfileModal } from "@/components/user/UserProfileModal";
import { Badge } from "@/components/ui/badge";
import { TablePagination } from "@/components/common/TablePagination";
import { toast } from "sonner";

const PAGE_SIZE = 10;

export function UsersPage() {
  const queryClient = useQueryClient();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserModel | null>(null);
  const [deletingUser, setDeletingUser] = useState<UserModel | null>(null);
  const [profileUser, setProfileUser] = useState<UserModel | null>(null);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["users", page],
    queryFn: () => usersService.list(page, PAGE_SIZE),
    placeholderData: (prev) => prev,
  });

  const users = data?.results;
  const totalItems = data?.count ?? 0;
  const totalPages = data?.total_pages ?? 1;

  const deleteMutation = useMutation({
    mutationFn: (employeeId: string) => usersService.remove(employeeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("User deleted successfully");
      setDeletingUser(null);
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "An error occurred while deleting the user"
      );
    },
  });

  const displayName = (user: UserModel) =>
    user.name ||
    (user.first_name || user.last_name
      ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
      : user.username) ||
    "N/A";

  const displayEmployeeId = (user: UserModel) =>
    user.employeeId || user.employee_id || user._id || "N/A";

  const statusBadgeClass = (active?: boolean) =>
    active
      ? "bg-green-600 hover:bg-green-700 text-white font-medium border-transparent rounded-full px-3"
      : "bg-slate-300 text-slate-700 font-medium border-transparent rounded-full px-3";

  const ActionButtons = ({ user }: { user: UserModel }) => (
    <div className="flex items-center justify-end gap-1">
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-muted-foreground hover:text-foreground"
        onClick={() => setEditingUser(user)}
        aria-label="Edit user"
      >
        <Pencil size={16} />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 text-muted-foreground hover:text-destructive"
        onClick={() => setDeletingUser(user)}
        aria-label="Delete user"
      >
        <Trash2 size={16} />
      </Button>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      {/* Header Area */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            <User size={28} className="text-primary" />
            Users
          </h1>
          <p className="text-muted-foreground mt-1">Manage system users and access</p>
        </div>
        <Button 
          onClick={() => setIsFormOpen(true)}
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground flex items-center justify-center gap-2 sm:w-auto"
        >
          <Plus size={16} />
          New User
        </Button>
      </div>

      {/* Table Area — desktop (md and up) */}
      <div className="hidden border rounded-xl bg-card shadow-sm overflow-hidden md:block">
        <div className="w-full overflow-x-auto">
        <Table className="min-w-[760px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[250px]">Name</TableHead>
              <TableHead>Employee ID</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Office</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  Loading users...
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-destructive">
                  Error loading users. Please try again.
                </TableCell>
              </TableRow>
            ) : users?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  No users found.
                </TableCell>
              </TableRow>
            ) : (
              users?.map((user: UserModel) => (
                <TableRow key={user.id}>
                  <TableCell className="py-4">
                    <button
                      className="font-medium text-foreground hover:text-[hsl(209,100%,32%)] hover:underline text-left"
                      onClick={() => setProfileUser(user)}
                    >
                      {displayName(user)}
                    </button>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {displayEmployeeId(user)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{user.email || "N/A"}</TableCell>
                  <TableCell className="text-muted-foreground">{user.working_office || user.office_name || "N/A"}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="bg-background text-foreground border-border font-normal capitalize">
                      {user.role || "User"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={statusBadgeClass(user.is_active)}>
                      {user.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <ActionButtons user={user} />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        </div>
      </div>

      {/* Card list — mobile (below md) */}
      <div className="flex flex-col gap-3 md:hidden">
        {isLoading ? (
          <div className="border rounded-xl bg-card p-6 text-center text-muted-foreground shadow-sm">
            Loading users...
          </div>
        ) : isError ? (
          <div className="border rounded-xl bg-card p-6 text-center text-destructive shadow-sm">
            Error loading users. Please try again.
          </div>
        ) : users?.length === 0 ? (
          <div className="border rounded-xl bg-card p-6 text-center text-muted-foreground shadow-sm">
            No users found.
          </div>
        ) : (
          users?.map((user: UserModel) => (
            <div
              key={user.id}
              className="border rounded-xl bg-card p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <button
                    className="font-medium text-foreground hover:text-[hsl(209,100%,32%)] hover:underline truncate text-left"
                    onClick={() => setProfileUser(user)}
                  >
                    {displayName(user)}
                  </button>
                  <p className="text-sm text-muted-foreground">
                    {displayEmployeeId(user)}
                  </p>
                </div>
                <ActionButtons user={user} />
              </div>

              <dl className="mt-3 grid grid-cols-1 gap-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Email</dt>
                  <dd className="text-right break-all">{user.email || "N/A"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Office</dt>
                  <dd className="text-right">{user.working_office || user.office_name || "N/A"}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Role</dt>
                  <dd>
                    <Badge variant="outline" className="bg-background text-foreground border-border font-normal capitalize">
                      {user.role || "User"}
                    </Badge>
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>
                    <Badge className={statusBadgeClass(user.is_active)}>
                      {user.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </dd>
                </div>
              </dl>
            </div>
          ))
        )}
      </div>

      {!isLoading && !isError && totalItems > 0 && (
        <div className="rounded-xl border bg-card shadow-sm">
          <TablePagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
            totalItems={totalItems}
            pageSize={PAGE_SIZE}
          />
        </div>
      )}

      <UserFormModal
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
      />

      <UserEditModal
        isOpen={!!editingUser}
        user={editingUser}
        onClose={() => setEditingUser(null)}
      />

      <UserProfileModal
        user={profileUser}
        isOpen={!!profileUser}
        onClose={() => setProfileUser(null)}
      />

      <AlertDialog
        open={!!deletingUser}
        onOpenChange={(open) => !open && setDeletingUser(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete user?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete{" "}
              <span className="font-medium text-foreground">
                {deletingUser?.name ||
                  deletingUser?.employeeId ||
                  deletingUser?.employee_id}
              </span>
              . This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
              onClick={(e) => {
                e.preventDefault();
                const id =
                  deletingUser?.employeeId || deletingUser?.employee_id;
                if (id) deleteMutation.mutate(id);
              }}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
