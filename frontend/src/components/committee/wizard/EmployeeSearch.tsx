
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, UserPlus, Loader2, AlertTriangle, Wifi, WifiOff } from "lucide-react";
import { toast } from "sonner";
import { employeesApi } from "@/services/api/employees";
import type { Employee } from "@/types/employee";

interface EmployeeSearchProps {
  onSelectEmployee: (employee: Employee) => void;
  excludeIds?: string[];
}



// Mock data for fallback when API is unavailable
const mockEmployees: Employee[] = [
  {
    id: 1,
    employee_id: "EMP001",
    name: "John Doe",
    email: "john.doe@company.com",
    phone: "+1234567890",
    department: "Engineering",
    designation: "Senior Developer",
    dateJoined: "2023-01-15",
    isActive: true,
  },
  {
    id: 2,
    employee_id: "EMP002",
    name: "Jane Smith",
    email: "jane.smith@company.com",
    phone: "+1234567891",
    department: "Marketing",
    designation: "Marketing Manager",
    dateJoined: "2023-02-20",
    isActive: true,
  },
  {
    id: 3,
    employee_id: "EMP003",
    name: "Mike Johnson",
    email: "mike.johnson@company.com",
    phone: "+1234567892",
    department: "HR",
    designation: "HR Specialist",
    dateJoined: "2023-03-10",
    isActive: true,
  }
];

const EmployeeSearch = ({ onSelectEmployee, excludeIds = [] }: EmployeeSearchProps) => {
  const [searchTerm, setSearchTerm] = useState("");

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [retryCount, setRetryCount] = useState(0);


  const maxRetries = 2;

  const filterEmployees = (list: Employee[], term: string) => {
    const searchStr = term.toLowerCase();
    const normalized = (value: string | undefined | null) => String(value || "").toLowerCase();

    return list.filter((emp) => {
      const idValue = normalized(emp.employee_id || (emp as any).employeeId);
      const nameValue = normalized(emp.name);
      const emailValue = normalized(emp.email);

      return (
        nameValue.includes(searchStr) ||
        idValue.includes(searchStr) ||
        emailValue.includes(searchStr)
      );
    });
  };

  const searchEmployees = async (term: string, attempt: number = 0) => {
    if (term.length < 2) {
      setEmployees([]);
      setShowResults(false);
      setError(null);
      setIsOfflineMode(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      console.log(`Searching employees - attempt ${attempt + 1}:`, {
        term,
        endpoint: '/api/employees/',
        params: { search: term, page_size: 50 }
      });

      const searchResults = await employeesApi.search(term);
      console.log('API search successful:', searchResults);

      // Filter out already selected employees
      const filteredEmployees = filterEmployees(searchResults, term).filter(
        (emp: Employee) => !excludeIds.includes(emp.employee_id) && !excludeIds.includes(emp.id?.toString())
      );

      setEmployees(filteredEmployees);
      setShowResults(true);
      setIsOfflineMode(false);
      setRetryCount(0);

    } catch (error) {
      console.error(`Employee search failed - attempt ${attempt + 1}:`, error);

      // Check if we should retry
      if (attempt < maxRetries && shouldRetry(error)) {
        console.log(`Retrying search in ${(attempt + 1) * 1000}ms...`);
        setTimeout(() => {
          setRetryCount(attempt + 1);
          searchEmployees(term, attempt + 1);
        }, (attempt + 1) * 1000);
        return;
      }

      // Use fallback mock data for certain error types
      if (shouldUseFallback(error)) {
        console.log('Using fallback mock data');
        const mockResults = filterMockEmployees(term);
        setEmployees(mockResults);
        setIsOfflineMode(true);
        setShowResults(true);

        toast("Using Offline Data", {
          description: "API unavailable. Showing sample employees for testing.",
        });
      } else {
        const errorMessage = getErrorMessage(error);
        setError(errorMessage);
        setEmployees([]);
        setShowResults(true);

        toast.error("Search Error", {
          description: errorMessage,
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const shouldRetry = (error: any): boolean => {
    // Retry on network errors, timeouts, and 5xx server errors
    return (
      error?.code === 'NETWORK_ERROR' ||
      error?.code === 'ECONNREFUSED' ||
      error?.response?.status >= 500 ||
      error?.message?.includes('timeout')
    );
  };

  const shouldUseFallback = (error: any): boolean => {
    // Use fallback for network connectivity issues
    return (
      error?.code === 'NETWORK_ERROR' ||
      error?.code === 'ECONNREFUSED' ||
      error?.message?.includes('Network Error') ||
      !navigator.onLine
    );
  };

  const getErrorMessage = (error: any): string => {
    if (error?.response?.status === 404) {
      return "Employee search endpoint not found. Please contact system administrator.";
    }
    if (error?.response?.status === 401) {
      return "Authentication required. Please log in again.";
    }
    if (error?.response?.status === 403) {
      return "You don't have permission to search employees.";
    }
    if (error?.response?.status >= 500) {
      return "Server error. Please try again later.";
    }
    if (error?.code === 'NETWORK_ERROR' || error?.code === 'ECONNREFUSED') {
      return "Unable to connect to server. Check your internet connection.";
    }
    return error?.message || "Failed to search employees. Please try again.";
  };

  const filterMockEmployees = (term: string): Employee[] => {
    return filterEmployees(mockEmployees, term)
      .filter(emp => !excludeIds.includes(emp.employee_id) && !excludeIds.includes(emp.id?.toString()));
  };

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchEmployees(searchTerm);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, excludeIds]);

  const handleSelectEmployee = (employee: Employee) => {
    const transformedEmployee = {
      ...employee,
      employeeId: employee.employee_id || employee.employeeId,
    };

    onSelectEmployee(transformedEmployee);
    setSearchTerm("");
    setShowResults(false);
    setEmployees([]);
    setError(null);
    setIsOfflineMode(false);
  };

  const handleRetry = () => {
    setRetryCount(0);
    searchEmployees(searchTerm);
  };

  return (
    <div className="relative space-y-2">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search employees by Name, ID, or Email"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
        {isLoading && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex items-center gap-2">
            {retryCount > 0 && (
              <span className="text-xs text-muted-foreground">Retry {retryCount}</span>
            )}
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
        )}
        {isOfflineMode && (
          <WifiOff className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-amber-500" />
        )}
      </div>

      {showResults && (
        <Card className="absolute top-full left-0 right-0 z-50 mt-1 max-h-60 overflow-y-auto">
          <CardContent className="p-2">
            {isOfflineMode && (
              <div className="mb-2 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-center gap-2 text-amber-700">
                  <WifiOff className="w-4 h-4" />
                  <span className="text-sm font-medium">Offline Mode</span>
                </div>
                <p className="text-xs text-amber-600 mt-1">
                  Showing sample data. API connection unavailable.
                </p>
              </div>
            )}

            {error ? (
              <div className="text-center py-4">
                <div className="flex items-center justify-center gap-2 text-destructive mb-2">
                  <AlertTriangle className="w-5 h-5" />
                  <p className="font-medium">Search Error</p>
                </div>
                <p className="text-sm text-muted-foreground mb-3">{error}</p>
                <Button variant="outline" size="sm" onClick={handleRetry}>
                  Try Again
                </Button>
              </div>
            ) : employees.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                {searchTerm.length >= 2 ? (
                  <>
                    <p className="font-medium">No employees found</p>
                    <p className="text-sm">Try searching with a different term</p>
                  </>
                ) : (
                  <p className="text-sm">Type at least 2 characters to search</p>
                )}
              </div>
            ) : (
              <div className="space-y-1">
                {employees.map((employee, index) => {
                  // Create a unique, stable key combining multiple identifiers
                  const uniqueKey = `employee-${employee.id || employee.employee_id || employee.employeeId || index}-${employee.email || index}`;

                  return (
                    <Button
                      key={uniqueKey}
                      variant="default"
                      onClick={() => handleSelectEmployee(employee)}
                      className="w-full justify-start p-3 h-auto bg-primary text-white hover:bg-primary/90 border-none mb-1 shadow-sm"
                    >
                      <div className="flex items-center gap-3 w-full">
                        <UserPlus className="w-4 h-4 flex-shrink-0 text-white" />
                        <div className="flex-1 text-left">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-white">{employee.name}</span>
                            {isOfflineMode && (
                              <Badge variant="secondary" className="text-xs bg-white/20 text-white border-none">
                                Sample
                              </Badge>
                            )}
                          </div>
                          <div className="text-sm text-blue-100/90 font-medium">
                            {employee.employee_id} • {employee.email}
                          </div>
                          {(employee.office?.name || employee.department) && (
                            <Badge variant="secondary" className="text-xs mt-1 bg-white text-primary font-medium border-none px-2 py-0">
                              {employee.office?.name || employee.department}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </Button>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default EmployeeSearch;
