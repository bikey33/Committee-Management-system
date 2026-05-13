import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Plus, User } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { usersService, User as UserModel } from "@/api/users";
import { UserFormModal } from "@/components/user/UserFormModal";
import { Badge } from "@/components/ui/badge";

export function UsersPage() {
  const [isFormOpen, setIsFormOpen] = useState(false);

  const { data: users, isLoading, isError } = useQuery({
    queryKey: ["users"],
    queryFn: usersService.getAll,
  });

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

      {/* Table Area */}
      <div className="border rounded-xl bg-card shadow-sm overflow-hidden">
        <div className="w-full overflow-x-auto">
        <Table className="min-w-[900px]">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[250px]">Name</TableHead>
              <TableHead>Employee ID</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Office</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  Loading users...
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-destructive">
                  Error loading users. Please try again.
                </TableCell>
              </TableRow>
            ) : users?.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                  No users found.
                </TableCell>
              </TableRow>
            ) : (
              users?.map((user: UserModel) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium text-foreground py-4">
                    {user.first_name || user.last_name ? `${user.first_name} ${user.last_name}` : user.username}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{user.employee_id}</TableCell>
                  <TableCell className="text-muted-foreground">{user.email || "N/A"}</TableCell>
                  <TableCell className="text-muted-foreground">{user.office_name || "N/A"}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className="bg-background text-foreground border-border font-normal capitalize">
                      {user.role || "User"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={user.is_active ? "bg-green-600 hover:bg-green-700 text-white font-medium border-transparent rounded-full px-3" : "bg-slate-300 text-slate-700 font-medium border-transparent rounded-full px-3"}>
                      {user.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        </div>
      </div>

      <UserFormModal 
        isOpen={isFormOpen} 
        onClose={() => setIsFormOpen(false)} 
      />
    </div>
  );
}
