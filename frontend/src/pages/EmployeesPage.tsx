import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Contact, Pencil, Search } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { TablePagination } from "@/components/common/TablePagination";
import { employeesService, Employee } from "@/api/employees";
import { EmployeeFormModal } from "@/components/employee/EmployeeFormModal";

const PAGE_SIZE = 10;

export function EmployeesPage() {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["employees", page, search],
    queryFn: () => employeesService.list(page, PAGE_SIZE, search),
    placeholderData: (prev) => prev,
  });

  const employees = data?.results;
  const totalItems = data?.count ?? 0;
  const totalPages = data?.total_pages ?? 1;

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  };

  const openCreate = () => {
    setEditingEmployee(null);
    setIsFormOpen(true);
  };

  const openEdit = (employee: Employee) => {
    setEditingEmployee(employee);
    setIsFormOpen(true);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
            <Contact size={28} className="text-primary" />
            Employees
          </h1>
          <p className="text-muted-foreground mt-1">
            The employee directory. User accounts are created from these employees.
          </p>
        </div>
        <Button
          onClick={openCreate}
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground flex items-center justify-center gap-2 sm:w-auto"
        >
          <Plus size={16} />
          New Employee
        </Button>
      </div>

      {/* Search */}
      <form onSubmit={submitSearch} className="flex gap-2">
        <div className="relative flex-1 sm:max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by name, ID, email, position…"
            className="pl-9"
          />
        </div>
        <Button type="submit" variant="outline">
          Search
        </Button>
        {search && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setSearchInput("");
              setSearch("");
              setPage(1);
            }}
          >
            Clear
          </Button>
        )}
      </form>

      {/* Desktop table */}
      <div className="hidden border rounded-xl bg-card shadow-sm overflow-hidden md:block">
        <div className="w-full overflow-x-auto">
          <Table className="min-w-[820px]">
            <TableHeader>
              <TableRow>
                <TableHead>Employee ID</TableHead>
                <TableHead className="w-[220px]">Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Account</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    Loading employees...
                  </TableCell>
                </TableRow>
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-destructive">
                    Error loading employees. Please try again.
                  </TableCell>
                </TableRow>
              ) : employees?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No employees found.
                  </TableCell>
                </TableRow>
              ) : (
                employees?.map((emp: Employee) => (
                  <TableRow key={emp.employee_id}>
                    <TableCell className="font-medium text-foreground py-4">{emp.employee_id}</TableCell>
                    <TableCell>{emp.name || "N/A"}</TableCell>
                    <TableCell className="text-muted-foreground">{emp.email || "N/A"}</TableCell>
                    <TableCell className="text-muted-foreground">{emp.phone || emp.mno || "N/A"}</TableCell>
                    <TableCell className="text-muted-foreground">{emp.department || "N/A"}</TableCell>
                    <TableCell>
                      {emp.has_user_account ? (
                        <Badge className="bg-green-600 hover:bg-green-700 text-white font-medium border-transparent rounded-full px-3">
                          Has account
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-muted-foreground rounded-full px-3">
                          No account
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-foreground"
                        onClick={() => openEdit(emp)}
                        aria-label="Edit employee"
                      >
                        <Pencil size={16} />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Mobile cards */}
      <div className="flex flex-col gap-3 md:hidden">
        {isLoading ? (
          <div className="border rounded-xl bg-card p-6 text-center text-muted-foreground shadow-sm">
            Loading employees...
          </div>
        ) : isError ? (
          <div className="border rounded-xl bg-card p-6 text-center text-destructive shadow-sm">
            Error loading employees. Please try again.
          </div>
        ) : employees?.length === 0 ? (
          <div className="border rounded-xl bg-card p-6 text-center text-muted-foreground shadow-sm">
            No employees found.
          </div>
        ) : (
          employees?.map((emp: Employee) => (
            <div key={emp.employee_id} className="border rounded-xl bg-card p-4 shadow-sm">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium text-foreground truncate">{emp.name || "N/A"}</p>
                  <p className="text-sm text-muted-foreground">{emp.employee_id}</p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  onClick={() => openEdit(emp)}
                  aria-label="Edit employee"
                >
                  <Pencil size={16} />
                </Button>
              </div>
              <dl className="mt-3 grid grid-cols-1 gap-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Email</dt>
                  <dd className="text-right break-all">{emp.email || "N/A"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Phone</dt>
                  <dd className="text-right">{emp.phone || emp.mno || "N/A"}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-muted-foreground">Department</dt>
                  <dd className="text-right">{emp.department || "N/A"}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Account</dt>
                  <dd>
                    {emp.has_user_account ? (
                      <Badge className="bg-green-600 hover:bg-green-700 text-white font-medium border-transparent rounded-full px-3">
                        Has account
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-muted-foreground rounded-full px-3">
                        No account
                      </Badge>
                    )}
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

      <EmployeeFormModal
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        employeeToEdit={editingEmployee}
      />
    </div>
  );
}
