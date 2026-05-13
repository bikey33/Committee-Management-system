// CommitteeUpdate.tsx
import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Plus, X, Check, ChevronsUpDown } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command";
import { cn } from "@/lib/utils";
import type { Committee } from "@/types/committee";
import EmployeeSearch from "@/components/committee/wizard/EmployeeSearch";
import type { Employee } from "@/types/employee";
import { useCommitteeRoles } from "@/hooks/useCommitteeRoles";

interface Member {
  id: string;
  employeeId: string;
  name: string;
  email: string;
  role: string;
  department?: string;
  phone?: string;
  designation?: string;
  isLoading?: boolean;
}

const CommitteeUpdate = () => {
  const { committeeId } = useParams<{ committeeId: string }>();
  const navigate = useNavigate();
  const { hasPermission, token } = useAuth();
  const { toast } = useToast();

  const [committee, setCommittee] = useState<Committee | null>(null);
  const [procurementPlans, setProcurementPlans] = useState<{ id: number; project_name: string }[]>([]);
  const [selectedProcurementPlan, setSelectedProcurementPlan] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [formData, setFormData] = useState({
    name: "",
    purpose: "",
    committee_type: "",
    formation_date: "",
    specification_submission_date: "",
    review_date: "",
    schedule: "",
    members: [] as Member[],
    formation_letter: null as File | null,
    should_notify: false,
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const { roles: committeeRoles, isLoading: loadingRoles } = useCommitteeRoles();

  const filteredProcurementPlans = procurementPlans.filter((plan) =>
    plan.project_name.toLowerCase().includes(searchInput.toLowerCase())
  );

  const generateMemberId = () => `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  const debounce = <T extends (...args: any[]) => void>(func: T, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: Parameters<T>) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  };

  const fetchEmployeeData = useCallback(
    async (index: number, employeeId: string) => {
      try {
        setFormData((prev) => ({
          ...prev,
          members: prev.members.map((m, i) =>
            i === index ? { ...m, isLoading: true } : m
          ),
        }));
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/users/employee/${employeeId}/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error("Employee not found");
        const { data: { user } } = await response.json();
        setFormData((prev) => ({
          ...prev,
          members: prev.members.map((m, i) =>
            i === index
              ? {
                  ...m,
                  employeeId: user.employee_id || employeeId,
                  name: user.name || "",
                  email: user.email || "",
                  department: user.department || "",
                  phone: user.phoneNumber || "",
                  designation: user.designation || "",
                  isLoading: false,
                }
              : m
          ),
        }));
        toast({
          title: "Employee Data Loaded",
          description: `${user.name}'s information has been auto-filled`,
        });
      } catch (error) {
        setFormData((prev) => ({
          ...prev,
          members: prev.members.map((m, i) =>
            i === index ? { ...m, isLoading: false } : m
          ),
        }));
        toast({
          title: "Error",
          description: `No record found for ID: ${employeeId}`,
          variant: "destructive",
        });
      }
    },
    [token, toast]
  );

  const debouncedFetchEmployeeData = useCallback(
    debounce((index: number, employeeId: string) => fetchEmployeeData(index, employeeId), 500),
    [fetchEmployeeData]
  );

  const handleAddMember = async () => {
    const newMember = {
      id: generateMemberId(),
      employeeId: "",
      name: "",
      email: "",
      role: "member",
      department: "",
      phone: "",
      designation: "",
      isLoading: false,
    };
    setFormData((prev) => ({
      ...prev,
      members: [...prev.members, newMember],
    }));
  };

  const handleUpdateMember = (index: number, field: keyof Member, value: string) => {
    setFormData((prev) => ({
      ...prev,
      members: prev.members.map((m, i) =>
        i === index ? { ...m, [field]: value } : m
      ),
    }));
    if (field === "employeeId" && value.length >= 6 && committeeId) {
      debouncedFetchEmployeeData(index, value);
      handleAddMemberToBackend(index, value, formData.members[index].role);
    }
  };

  const handleEmployeeSelect = (employee: Employee) => {
    const employeeId = employee.employee_id || (employee as any).employeeId || "";
    if (!employeeId) return;

    const newIndex = formData.members.length;
    const newMember: Member = {
      id: generateMemberId(),
      employeeId,
      name: employee.name || "",
      email: employee.email || "",
      role: "member",
      department: employee.department || "",
      phone: employee.phone || "",
      designation: employee.designation || "",
      isLoading: false,
    };

    setFormData((prev) => ({
      ...prev,
      members: [...prev.members, newMember],
    }));

    handleAddMemberToBackend(newIndex, employeeId, "member");
  };

  const handleAddMemberToBackend = async (index: number, employeeId: string, role: string) => {
    if (!committeeId || !token || !employeeId) return;

    try {
      setFormData((prev) => ({
        ...prev,
        members: prev.members.map((m, i) =>
          i === index ? { ...m, isLoading: true } : m
        ),
      }));
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/addmember/${committeeId}/`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ employeeId, committeeRole: role || "member" }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.message || `Failed to add member: ${response.status}`;
        throw new Error(errorMessage);
      }

      const { data: { committee: updatedCommittee } } = await response.json();
      const newMember = updatedCommittee.membersList.find(
        (m: any) => m.employeeId === employeeId
      );

      if (newMember) {
        setFormData((prev) => ({
          ...prev,
          members: prev.members.map((m, i) =>
            i === index
              ? {
                  ...m,
                  id: newMember._id || m.id,
                  employeeId: newMember.employeeId,
                  name: newMember.name,
                  email: newMember.email,
                  role: newMember.role,
                  department: newMember.department || "",
                  phone: newMember.phone || "",
                  designation: newMember.designation || "",
                  isLoading: false,
                }
              : m
          ),
        }));
        toast({
          title: "Member Added",
          description: `${newMember.name} has been added to the committee.`,
        });
      }
    } catch (error) {
      setFormData((prev) => ({
        ...prev,
        members: prev.members.map((m, i) =>
          i === index ? { ...m, isLoading: false } : m
        ),
      }));
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to add member",
        variant: "destructive",
      });
    }
  };

  const handleRemoveMember = async (index: number) => {
    const member = formData.members[index];
    if (!member.employeeId || !committeeId) {
      setFormData((prev) => ({
        ...prev,
        members: prev.members.filter((_, i) => i !== index),
      }));
      return;
    }

    try {
      const deleteResponse = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/members/${member.employeeId}/`,
        {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (!deleteResponse.ok) {
        const errorData = await deleteResponse.json().catch(() => ({}));
        const errorMessage = errorData.message || `Failed to remove member: ${deleteResponse.status}`;
        throw new Error(errorMessage);
      }

      setFormData((prev) => ({
        ...prev,
        members: prev.members.filter((_, i) => i !== index),
      }));
      toast({
        title: "Member Removed",
        description: "Committee member has been removed successfully.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to remove member",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    if (!hasPermission("manage_committees")) {
      toast({
        title: "Access Denied",
        description: "You do not have permission to edit committees.",
        variant: "destructive",
      });
      navigate("/");
      return;
    }

    const fetchProcurementPlans = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/procurement/plans/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error("Failed to fetch procurement plans");
        const responseData = await response.json();
        const plans = Array.isArray(responseData)
          ? responseData
          : (responseData?.results || responseData?.data || []);
        setProcurementPlans(plans);
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to load procurement plans",
          variant: "destructive",
        });
      }
    };

    const fetchCommittee = async () => {
      if (!committeeId || !token) return;

      try {
        const response = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch committee: ${response.status}`);
        }

        const data = await response.json();
        const committeeData = data.data?.committee || data;

        const formatDate = (date: string | null | undefined): string => {
          if (!date) return "";
          let parsedDate: Date;
          if (date.includes("/")) {
            const [month, day, year] = date.split("/").map(Number);
            parsedDate = new Date(year, month - 1, day);
          } else {
            parsedDate = new Date(date);
          }
          return isNaN(parsedDate.getTime()) ? "" : parsedDate.toISOString().split("T")[0];
        };

        const members = Array.isArray(committeeData.membersList)
          ? committeeData.membersList.map((m: any) => ({
              id: m._id || generateMemberId(),
              employeeId: m.employeeId || "",
              name: m.name || "",
              email: m.email || "",
              role: m.role || "member",
              department: m.department || "",
              phone: m.phone || "",
              designation: m.designation || "",
              isLoading: false,
            })).filter((m: Member) => m.employeeId)
          : [];

        setCommittee(committeeData);
        setSelectedProcurementPlan(committeeData.procurement_plan?.toString() || null);
        setFormData({
          name: committeeData.name || "",
          purpose: committeeData.purpose || "",
          committee_type: committeeData.committee_type || "",
          formation_date: formatDate(committeeData.formation_date),
          specification_submission_date: formatDate(committeeData.specification_submission_date),
          review_date: formatDate(committeeData.review_date),
          schedule: committeeData.schedule || "",
          members,
          formation_letter: null,
          should_notify: committeeData.should_notify || false,
        });

        if (committeeData.formationLetterURL) {
          try {
            const fileResponse = await fetch(
              `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/download/`,
               {
                headers: { Authorization: `Bearer ${token}` },
              }
            );
            const blob = await fileResponse.blob();
            const file = new File(
              [blob],
              committeeData.formationLetterURL.split("/").pop() || "formation_letter.pdf",
              { type: blob.type }
            );
            setFormData((prev) => ({ ...prev, formation_letter: file }));
          } catch (error) {
            console.error("Error fetching file:", error);
          }
        }
      } catch (error) {
        toast({
          title: "Error",
          description: error instanceof Error ? error.message : "Failed to load committee data",
          variant: "destructive",
        });
        navigate("/");
      } finally {
        setLoading(false);
      }
    };

    fetchProcurementPlans();
    fetchCommittee();
  }, [committeeId, token, hasPermission, navigate, toast]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setFormData((prev) => ({ ...prev, formation_letter: file }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!committeeId) return;

    if (!formData.name || !formData.purpose || !formData.committee_type) {
      toast({
        title: "Validation Error",
        description: "Name, purpose, and committee type are required",
        variant: "destructive",
      });
      return;
    }

    if (formData.members.length === 0) {
      toast({
        title: "Validation Error",
        description: "At least one member is required",
        variant: "destructive",
      });
      return;
    }

    const invalidMembers = formData.members.filter(
      (m) => !m.employeeId || !m.name || !m.email
    );
    if (invalidMembers.length > 0) {
      toast({
        title: "Validation Error",
        description: "All members must have Employee ID, Name, and Email",
        variant: "destructive",
      });
      return;
    }

    const employeeIds = formData.members.map((m) => m.employeeId);
    if (new Set(employeeIds).size !== employeeIds.length) {
      toast({
        title: "Validation Error",
        description: "Duplicate employee IDs are not allowed",
        variant: "destructive",
      });
      return;
    }

    setSubmitting(true);

    const formDataToSend = new FormData();
    formDataToSend.append("name", formData.name);
    formDataToSend.append("purpose", formData.purpose);
    formDataToSend.append("committee_type", formData.committee_type);
    if (selectedProcurementPlan && selectedProcurementPlan !== "none") {
      formDataToSend.append("procurement_plan", selectedProcurementPlan);
    }
    if (formData.formation_date) {
      formDataToSend.append("formation_date", formData.formation_date);
    }
    if (formData.specification_submission_date) {
      formDataToSend.append("specification_submission_date", formData.specification_submission_date);
    }
    if (formData.review_date) {
      formDataToSend.append("review_date", formData.review_date);
    }
    if (formData.schedule) {
      formDataToSend.append("schedule", formData.schedule);
    }
    if (formData.formation_letter) {
      formDataToSend.append("formation_letter", formData.formation_letter);
    }
    formDataToSend.append("should_notify", String(formData.should_notify));
    const membersData = formData.members.map((m) => ({
      employeeId: m.employeeId,
      role: m.role || "member",
    }));
    formDataToSend.append("members", JSON.stringify(membersData));

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/update/${committeeId}/`,
        {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
          body: formDataToSend,
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || `Failed to update committee: ${response.status}`);
      }

      toast({
        title: "Update Successful",
        description: "Committee has been updated.",
      });
      navigate("/committee");
    } catch (error) {
      toast({
        title: "Update Failed",
        description: error instanceof Error ? error.message : "Failed to update committee",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const memoizedMembers = useMemo(() => formData.members, [formData.members]);

  if (loading || !committee) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600">Loading...</span>
      </div>
    );
  }

  return (
    <Card className="max-w-3xl mx-auto mt-8">
      <CardHeader>
        <CardTitle>Edit Committee</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="name">Committee Name *</Label>
            <Input
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              disabled={submitting}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="purpose">Purpose *</Label>
            <Textarea
              id="purpose"
              name="purpose"
              value={formData.purpose}
              onChange={handleChange}
              required
              disabled={submitting}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="committee_type">Committee Type *</Label>
            <Select
              value={formData.committee_type}
              onValueChange={(value) =>
                setFormData((prev) => ({ ...prev, committee_type: value }))
              }
              disabled={submitting}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select committee type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="specification">Specification</SelectItem>
                <SelectItem value="evaluation">Evaluation</SelectItem>
                <SelectItem value="review">Review</SelectItem>
                <SelectItem value="contract">Contract</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="procurement_plan">Procurement Plan</Label>
            <Popover open={open} onOpenChange={setOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={open}
                  className="w-full justify-between"
                  disabled={submitting}
                >
                  {selectedProcurementPlan
                    ? procurementPlans.find((plan) => plan.id.toString() === selectedProcurementPlan)?.project_name ||
                      "Select procurement plan"
                    : "Select procurement plan"}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-full p-0">
                <Command>
                  <CommandInput
                    placeholder="Search procurement plan..."
                    onValueChange={(value) => setSearchInput(typeof value === 'string' ? value : "")}
                  />
                  <CommandEmpty>No procurement plan found.</CommandEmpty>
                  <CommandGroup>
                    <CommandItem
                      value="none"
                      onSelect={() => {
                        setSelectedProcurementPlan(null);
                        setOpen(false);
                      }}
                    >
                      <Check
                        className={cn(
                          "mr-2 h-4 w-4",
                          selectedProcurementPlan === null ? "opacity-100" : "opacity-0"
                        )}
                      />
                      None
                    </CommandItem>
                    {filteredProcurementPlans.map((plan) => (
                      <CommandItem
                        key={plan.id}
                        value={plan.project_name}
                        onSelect={() => {
                          setSelectedProcurementPlan(plan.id.toString());
                          setOpen(false);
                        }}
                      >
                        <Check
                          className={cn(
                            "mr-2 h-4 w-4",
                            selectedProcurementPlan === plan.id.toString() ? "opacity-100" : "opacity-0"
                          )}
                        />
                        {plan.project_name}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="formation_date">Formation Date *</Label>
              <Input
                id="formation_date"
                name="formation_date"
                type="date"
                value={formData.formation_date}
                onChange={handleChange}
                required
                disabled={submitting}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="specification_submission_date">Specification Submission Date</Label>
              <Input
                id="specification_submission_date"
                name="specification_submission_date"
                type="date"
                value={formData.specification_submission_date}
                onChange={handleChange}
                disabled={submitting}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="review_date">Review Date</Label>
              <Input
                id="review_date"
                name="review_date"
                type="date"
                value={formData.review_date}
                onChange={handleChange}
                disabled={submitting}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="schedule">Schedule</Label>
            <Input
              id="schedule"
              name="schedule"
              value={formData.schedule}
              onChange={handleChange}
              disabled={submitting}
            />
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <Label>Committee Members *</Label>
              <Button
                type="button"
                onClick={handleAddMember}
                variant="outline"
                className="flex items-center gap-2"
                disabled={submitting}
              >
                <Plus className="h-4 w-4" />
                Add Member
              </Button>
            </div>
            <div className="space-y-2">
              <Label className="text-sm text-muted-foreground">Search and Add Employees</Label>
              <EmployeeSearch
                onSelectEmployee={handleEmployeeSelect}
                excludeIds={memoizedMembers.map((m) => m.employeeId).filter(Boolean)}
              />
            </div>
            <div className="space-y-4">
              {memoizedMembers.map((member, index) => (
                <div key={member.id} className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 border rounded-lg relative">
                  <div>
                    <Label htmlFor={`employee-id-${member.id}`}>Employee ID *</Label>
                    <Input
                      id={`employee-id-${member.id}`}
                      value={member.employeeId}
                      onChange={(e) => handleUpdateMember(index, "employeeId", e.target.value)}
                      placeholder="Enter ID (e.g., NTC001)"
                      required
                      disabled={submitting || member.isLoading}
                    />
                  </div>
                  <div>
                    <Label htmlFor={`name-${member.id}`}>Name *</Label>
                    <Input
                      id={`name-${member.id}`}
                      value={member.name}
                      onChange={(e) => handleUpdateMember(index, "name", e.target.value)}
                      placeholder="Full name"
                      required
                      disabled={submitting || member.isLoading}
                    />
                  </div>
                  <div>
                    <Label htmlFor={`email-${member.id}`}>Email *</Label>
                    <Input
                      id={`email-${member.id}`}
                      type="email"
                      value={member.email}
                      onChange={(e) => handleUpdateMember(index, "email", e.target.value)}
                      placeholder="email@example.com"
                      required
                      disabled={submitting || member.isLoading}
                    />
                  </div>
                  <div>
                    <Label htmlFor={`role-${member.id}`}>Role *</Label>
                    <select
                      id={`role-${member.id}`}
                      value={member.role}
                      onChange={(e) => handleUpdateMember(index, "role", e.target.value)}
                      className="w-full h-10 px-3 py-2 text-base rounded-md border border-input bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      disabled={submitting || member.isLoading || loadingRoles}
                    >
                      {committeeRoles.map((role) => (
                        <option key={role.id} value={role.value}>
                          {role.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute -right-2 -top-2"
                    onClick={() => handleRemoveMember(index)}
                    disabled={submitting || member.isLoading}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                  {member.isLoading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-50">
                      <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                    </div>
                  )}
                </div>
              ))}
              {memoizedMembers.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  No members added yet. Click "Add Member" to begin.
                </div>
              )}
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="formation_letter">Formation Letter</Label>
            <Input
              id="formation_letter"
              name="formation_letter"
              type="file"
              accept=".pdf,.doc,.docx"
              onChange={handleFileChange}
              disabled={submitting}
            />
            {committee.formationLetterURL && (
              <p className="text-sm text-gray-600">
                Current file: {committee.formationLetterURL.split("/").pop() || "Formation Letter"}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="should_notify">Notify Members</Label>
            <input
              id="should_notify"
              type="checkbox"
              checked={formData.should_notify}
              onChange={(e) => setFormData((prev) => ({ ...prev, should_notify: e.target.checked }))}
              disabled={submitting}
            />
          </div>
          <div className="flex justify-end space-x-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate("/committee")}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Updating...
                </>
              ) : (
                "Save Changes"
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default CommitteeUpdate;




// // CommitteeUpdate.tsx
// import { useState, useEffect, useCallback } from "react";
// import { useParams, useNavigate } from "react-router-dom";
// import {
//   Card,
//   CardContent,
//   CardHeader,
//   CardTitle,
// } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import { Label } from "@/components/ui/label";
// import { Textarea } from "@/components/ui/textarea";
// import { Loader2, Plus, X, Check, ChevronsUpDown } from "lucide-react";
// import { useAuth } from "@/contexts/AuthContext";
// import { useToast } from "@/hooks/use-toast";
// import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
// import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
// import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command";
// import { cn } from "@/lib/utils";
// import type { Committee, CommitteeMember } from "@/types/committee";

// interface Member {
//   employeeId: string;
//   name: string;
//   email: string;
//   role: string;
//   department?: string;
//   phone?: string;
//   designation?: string;
// }

// const CommitteeUpdate = () => {
//   const { committeeId } = useParams<{ committeeId: string }>();
//   const navigate = useNavigate();
//   const { hasPermission, token } = useAuth();
//   const { toast } = useToast();

//   const [committee, setCommittee] = useState<Committee | null>(null);
//   const [procurementPlans, setProcurementPlans] = useState<{ id: number; project_name: string }[]>([]);
//   const [selectedProcurementPlan, setSelectedProcurementPlan] = useState<string | null>(null);
//   const [open, setOpen] = useState(false);
//   const [searchInput, setSearchInput] = useState("");
//   const [formData, setFormData] = useState({
//     name: "",
//     purpose: "",
//     committee_type: "",
//     formation_date: "",
//     specification_submission_date: "",
//     review_date: "",
//     schedule: "",
//     members: [] as Member[],
//     formation_letter: null as File | null,
//     should_notify: false,
//   });
//   const [loading, setLoading] = useState(true);
//   const [submitting, setSubmitting] = useState(false);

//   const filteredProcurementPlans = procurementPlans.filter((plan) =>
//     plan.project_name.toLowerCase().includes(searchInput.toLowerCase())
//   );

//   // Debounce function to limit API calls
//   const debounce = <T extends (...args: any[]) => void>(func: T, wait: number) => {
//     let timeout: NodeJS.Timeout;
//     return (...args: Parameters<T>) => {
//       clearTimeout(timeout);
//       timeout = setTimeout(() => func(...args), wait);
//     };
//   };

//   const fetchEmployeeData = useCallback(
//     async (index: number, employeeId: string) => {
//       try {
//         const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/users/employee/${employeeId}/`, {
//           headers: { Authorization: `Bearer ${token}` },
//         });
//         if (!response.ok) throw new Error("Employee not found");
//         const { data: { user } } = await response.json();
//         setFormData((prev) => ({
//           ...prev,
//           members: prev.members.map((m, i) =>
//             i === index
//               ? {
//                   ...m,
//                   employeeId: user.employee_id || employeeId,
//                   name: user.name || "",
//                   email: user.email || "",
//                   department: user.department || "",
//                   phone: user.phoneNumber || "",
//                   designation: user.designation || "",
//                 }
//               : m
//           ),
//         }));
//         toast({
//           title: "Employee Data Loaded",
//           description: `${user.name}'s information has been auto-filled`,
//         });
//       } catch (error) {
//         console.error("Error fetching employee data:", error);
//         toast({
//           title: "Error",
//           description: `No record found for ID: ${employeeId}`,
//           variant: "destructive",
//         });
//       }
//     },
//     [token, toast]
//   );

//   // Debounced version of fetchEmployeeData
//   const debouncedFetchEmployeeData = useCallback(
//     debounce((index: number, employeeId: string) => fetchEmployeeData(index, employeeId), 500),
//     [fetchEmployeeData]
//   );

//   useEffect(() => {
//     if (!hasPermission("manage_committees")) {
//       toast({
//         title: "Access Denied",
//         description: "You do not have permission to edit committees.",
//         variant: "destructive",
//       });
//       navigate("/");
//       return;
//     }

//     const fetchProcurementPlans = async () => {
//       try {
//         const response = await fetch("${import.meta.env.VITE_API_BASE_URL}/api/procurement/plans/", {
//           headers: {
//             Authorization: `Bearer ${token}`,
//           },
//         });
//         if (!response.ok) throw new Error("Failed to fetch procurement plans");
//         const responseData = await response.json();
//         setProcurementPlans(responseData || []);
//       } catch (error) {
//         console.error("Error fetching procurement plans:", error);
//         toast({
//           title: "Error",
//           description: "Failed to load procurement plans",
//           variant: "destructive",
//         });
//       }
//     };

//     const fetchCommittee = async () => {
//       if (!committeeId || !token) return;

//       try {
//         const response = await fetch(
//           `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/`,
//           {
//             headers: {
//               Authorization: `Bearer ${token}`,
//             },
//           }
//         );

//         if (!response.ok) {
//           throw new Error(`Failed to fetch committee: ${response.status} ${response.statusText}`);
//         }

//         const data = await response.json();
//         console.log("Raw API response:", JSON.stringify(data, null, 2));

//         const committeeData = data.data?.committee || data;

//         const formatDate = (date: string | null | undefined): string => {
//           if (!date) return "";
//           let parsedDate: Date;
//           if (date.includes("/")) {
//             const [month, day, year] = date.split("/").map(Number);
//             parsedDate = new Date(year, month - 1, day);
//           } else {
//             parsedDate = new Date(date);
//           }
//           return isNaN(parsedDate.getTime()) ? "" : parsedDate.toISOString().split("T")[0];
//         };

//         const members = Array.isArray(committeeData.membersList)
//           ? committeeData.membersList.map((m: any) => ({
//               employeeId: m.employeeId || "",
//               name: m.name || "",
//               email: m.email || "",
//               role: m.role || "member",
//               department: m.department || "",
//               phone: m.phone || "",
//               designation: m.designation || "",
//             })).filter((m: Member) => m.employeeId)
//           : [];

//         setCommittee(committeeData);
//         setSelectedProcurementPlan(committeeData.procurement_plan?.toString() || null);
//         setFormData({
//           name: committeeData.name || "",
//           purpose: committeeData.purpose || "",
//           committee_type: committeeData.committee_type || "",
//           formation_date: formatDate(committeeData.formation_date),
//           specification_submission_date: formatDate(committeeData.specification_submission_date),
//           review_date: formatDate(committeeData.review_date),
//           schedule: committeeData.schedule || "",
//           members,
//           formation_letter: null,
//           should_notify: false,
//         });

//         if (committeeData.formationLetterURL) {
//           try {
//             const fileResponse = await fetch(
//               `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/download/${committeeId}/`,
//               {
//                 headers: { Authorization: `Bearer ${token}` },
//               }
//             );
//             const blob = await fileResponse.blob();
//             const file = new File(
//               [blob],
//               committeeData.formationLetterURL.split("/").pop() || "formation_letter.pdf",
//               { type: blob.type }
//             );
//             setFormData((prev) => ({ ...prev, formation_letter: file }));
//           } catch (error) {
//             console.error("Error fetching file:", error);
//           }
//         }
//       } catch (error) {
//         console.error("Error fetching committee:", error);
//         toast({
//           title: "Error",
//           description: error instanceof Error ? error.message : "Failed to load committee data",
//           variant: "destructive",
//         });
//         navigate("/");
//       } finally {
//         setLoading(false);
//       }
//     };

//     fetchProcurementPlans();
//     fetchCommittee();
//   }, [committeeId, token, hasPermission, navigate, toast]);

//   const handleChange = (
//     e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
//   ) => {
//     const { name, value } = e.target;
//     setFormData((prev) => ({ ...prev, [name]: value }));
//   };

//   const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
//     const file = e.target.files?.[0] || null;
//     setFormData((prev) => ({ ...prev, formation_letter: file }));
//   };

//   const handleAddMember = () => {
//     setFormData((prev) => ({
//       ...prev,
//       members: [
//         ...prev.members,
//         {
//           employeeId: "",
//           name: "",
//           email: "",
//           role: "member",
//           department: "",
//           phone: "",
//           designation: "",
//         },
//       ],
//     }));
//   };

//   const handleUpdateMember = (index: number, field: keyof Member, value: string) => {
//     setFormData((prev) => ({
//       ...prev,
//       members: prev.members.map((m, i) =>
//         i === index ? { ...m, [field]: value } : m
//       ),
//     }));

//     if (field === "employeeId" && value.length >= 6) {
//       debouncedFetchEmployeeData(index, value);
//     }
//   };

//   const handleRemoveMember = async (index: number) => {
//     const member = formData.members[index];
//     if (member.employeeId) {
//       try {
//         const response = await fetch(
//           `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/`,
//           {
//             headers: {
//               Authorization: `Bearer ${token}`,
//             },
//           }
//         );
//         if (!response.ok) {
//           throw new Error(`Committee with ID ${committeeId} not found`);
//         }

//         const committeeData = await response.json();
//         const membersList = committeeData.data?.committee?.membersList || [];
//         const memberExists = membersList.some((m: any) => m.employeeId === member.employeeId);
//         if (!memberExists) {
//           throw new Error(`Employee ${member.employeeId} is not a member of this committee`);
//         }

//         const deleteResponse = await fetch(
//           `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/members/${member.employeeId}/`,
//           {
//             method: "DELETE",
//             headers: {
//               Authorization: `Bearer ${token}`,
//             },
//           }
//         );

//         if (!deleteResponse.ok) {
//           const errorData = await deleteResponse.json().catch(() => ({}));
//           const errorMessage = errorData.message || errorData.error?.message || `Failed to remove member: ${deleteResponse.status}`;
//           throw new Error(errorMessage);
//         }
//       } catch (error) {
//         console.error("Error removing member:", error);
//         toast({
//           title: "Error",
//           description: error instanceof Error ? error.message : "Failed to remove member",
//           variant: "destructive",
//         });
//         return;
//       }
//     }
//     setFormData((prev) => ({
//       ...prev,
//       members: prev.members.filter((_, i) => i !== index),
//     }));
//     toast({
//       title: "Member Removed",
//       description: "Committee member has been removed successfully.",
//     });
//   };

//   const handleSubmit = async (e: React.FormEvent) => {
//     e.preventDefault();
//     if (!committeeId) return;

//     if (!formData.name || !formData.purpose || !formData.committee_type) {
//       toast({
//         title: "Validation Error",
//         description: "Name, purpose, and committee type are required",
//         variant: "destructive",
//       });
//       return;
//     }

//     if (formData.members.length === 0) {
//       toast({
//         title: "Validation Error",
//         description: "At least one member is required",
//         variant: "destructive",
//       });
//       return;
//     }

//     const invalidMembers = formData.members.filter(
//       (m) => !m.employeeId || !m.name || !m.email
//     );
//     if (invalidMembers.length > 0) {
//       toast({
//         title: "Validation Error",
//         description: "All members must have Employee ID, Name, and Email",
//         variant: "destructive",
//       });
//       return;
//     }

//     const employeeIds = formData.members.map((m) => m.employeeId);
//     if (new Set(employeeIds).size !== employeeIds.length) {
//       toast({
//         title: "Validation Error",
//         description: "Duplicate employee IDs are not allowed",
//         variant: "destructive",
//       });
//       return;
//     }

//     setSubmitting(true);

//     const formDataToSend = new FormData();
//     formDataToSend.append("name", formData.name);
//     formDataToSend.append("purpose", formData.purpose);
//     formDataToSend.append("committee_type", formData.committee_type);
//     if (selectedProcurementPlan && selectedProcurementPlan !== "none") {
//       formDataToSend.append("procurement_plan", selectedProcurementPlan);
//     }
//     if (formData.formation_date) {
//       formDataToSend.append("formation_date", formData.formation_date);
//     }
//     if (formData.specification_submission_date) {
//       formDataToSend.append("specification_submission_date", formData.specification_submission_date);
//     }
//     if (formData.review_date) {
//       formDataToSend.append("review_date", formData.review_date);
//     }
//     if (formData.schedule) {
//       formDataToSend.append("schedule", formData.schedule);
//     }
//     if (formData.formation_letter) {
//       formDataToSend.append("formation_letter", formData.formation_letter);
//     }
//     formDataToSend.append("should_notify", String(formData.should_notify));

//     try {
//       const response = await fetch(
//         `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/update/${committeeId}/`,
//         {
//           method: "PATCH",
//           headers: {
//             Authorization: `Bearer ${token}`,
//           },
//           body: formDataToSend,
//         }
//       );

//       const data = await response.json();
//       if (!response.ok) {
//         throw new Error(data.message || `Failed to update committee: ${response.status}`);
//       }

//       // Fetch current committee members to determine new additions
//       const committeeResponse = await fetch(
//         `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/`,
//         {
//           headers: {
//             Authorization: `Bearer ${token}`,
//           },
//         }
//       );
//       if (!committeeResponse.ok) {
//         throw new Error("Failed to fetch committee data");
//       }
//       const committeeData = await committeeResponse.json();
//       const currentMembers = committeeData.data?.committee?.membersList || [];

//       // Add new members to the committee
//       for (const member of formData.members) {
//         const isExistingMember = currentMembers.some(
//           (m: any) => m.employeeId === member.employeeId
//         );
//         if (!isExistingMember) {
//           const addMemberResponse = await fetch(
//             `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/addmember/${committeeId}/`,
//             {
//               method: "POST",
//               headers: {
//                 Authorization: `Bearer ${token}`,
//                 "Content-Type": "application/json",
//               },
//               body: JSON.stringify({
//                 employeeId: member.employeeId,
//                 committeeRole: member.role || "member",
//               }),
//             }
//           );

//           if (!addMemberResponse.ok) {
//             const errorData = await addMemberResponse.json().catch(() => ({}));
//             throw new Error(errorData.message || `Failed to add member ${member.employeeId}: ${addMemberResponse.status}`);
//           }
//         }
//       }

//       toast({
//         title: "Update Successful",
//         description: "Committee has been updated.",
//       });
//       navigate("/committees");
//     } catch (error) {
//       console.error("Error updating committee:", error);
//       toast({
//         title: "Update Failed",
//         description: error instanceof Error ? error.message : "Failed to update committee",
//         variant: "destructive",
//       });
//     } finally {
//       setSubmitting(false);
//     }
//   };

//   if (loading || !committee) {
//     return (
//       <div className="flex justify-center items-center h-64">
//         <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
//         <span className="ml-2 text-gray-600">Loading...</span>
//       </div>
//     );
//   }

//   return (
//     <Card className="max-w-3xl mx-auto mt-8">
//       <CardHeader>
//         <CardTitle>Edit Committee</CardTitle>
//       </CardHeader>
//       <CardContent>
//         <form onSubmit={handleSubmit} className="space-y-6">
//           <div className="space-y-2">
//             <Label htmlFor="name">Committee Name *</Label>
//             <Input
//               id="name"
//               name="name"
//               value={formData.name}
//               onChange={handleChange}
//               required
//               disabled={submitting}
//             />
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="purpose">Purpose *</Label>
//             <Textarea
//               id="purpose"
//               name="purpose"
//               value={formData.purpose}
//               onChange={handleChange}
//               required
//               disabled={submitting}
//             />
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="committee_type">Committee Type *</Label>
//             <Select
//               value={formData.committee_type}
//               onValueChange={(value) =>
//                 setFormData((prev) => ({ ...prev, committee_type: value }))
//               }
//               disabled={submitting}
//             >
//               <SelectTrigger>
//                 <SelectValue placeholder="Select committee type" />
//               </SelectTrigger>
//               <SelectContent>
//                 <SelectItem value="specification">Specification</SelectItem>
//                 <SelectItem value="evaluation">Evaluation</SelectItem>
//                 <SelectItem value="other">Other</SelectItem>
//               </SelectContent>
//             </Select>
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="procurement_plan">Procurement Plan</Label>
//             <Popover open={open} onOpenChange={setOpen}>
//               <PopoverTrigger asChild>
//                 <Button
//                   variant="outline"
//                   role="combobox"
//                   aria-expanded={open}
//                   className="w-full justify-between"
//                   disabled={submitting}
//                 >
//                   {selectedProcurementPlan
//                     ? procurementPlans.find((plan) => plan.id.toString() === selectedProcurementPlan)?.project_name ||
//                       "Select procurement plan"
//                     : "Select procurement plan"}
//                   <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
//                 </Button>
//               </PopoverTrigger>
//               <PopoverContent className="w-full p-0">
//                 <Command>
//                   <CommandInput
//                     placeholder="Search procurement plan..."
//                     onValueChange={(value) => setSearchInput(typeof value === 'string' ? value : "")}
//                   />
//                   <CommandEmpty>No procurement plan found.</CommandEmpty>
//                   <CommandGroup>
//                     <CommandItem
//                       value="none"
//                       onSelect={() => {
//                         setSelectedProcurementPlan(null);
//                         setOpen(false);
//                       }}
//                     >
//                       <Check
//                         className={cn(
//                           "mr-2 h-4 w-4",
//                           selectedProcurementPlan === null ? "opacity-100" : "opacity-0"
//                         )}
//                       />
//                       None
//                     </CommandItem>
//                     {filteredProcurementPlans.map((plan) => (
//                       <CommandItem
//                         key={plan.id}
//                         value={plan.project_name}
//                         onSelect={() => {
//                           setSelectedProcurementPlan(plan.id.toString());
//                           setOpen(false);
//                         }}
//                       >
//                         <Check
//                           className={cn(
//                             "mr-2 h-4 w-4",
//                             selectedProcurementPlan === plan.id.toString() ? "opacity-100" : "opacity-0"
//                           )}
//                         />
//                         {plan.project_name}
//                       </CommandItem>
//                     ))}
//                   </CommandGroup>
//                 </Command>
//               </PopoverContent>
//             </Popover>
//           </div>
//           <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
//             <div className="space-y-2">
//               <Label htmlFor="formation_date">Formation Date *</Label>
//               <Input
//                 id="formation_date"
//                 name="formation_date"
//                 type="date"
//                 value={formData.formation_date}
//                 onChange={handleChange}
//                 required
//                 disabled={submitting}
//               />
//             </div>
//             <div className="space-y-2">
//               <Label htmlFor="specification_submission_date">Specification Submission Date</Label>
//               <Input
//                 id="specification_submission_date"
//                 name="specification_submission_date"
//                 type="date"
//                 value={formData.specification_submission_date}
//                 onChange={handleChange}
//                 disabled={submitting}
//               />
//             </div>
//             <div className="space-y-2">
//               <Label htmlFor="review_date">Review Date</Label>
//               <Input
//                 id="review_date"
//                 name="review_date"
//                 type="date"
//                 value={formData.review_date}
//                 onChange={handleChange}
//                 disabled={submitting}
//               />
//             </div>
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="schedule">Schedule</Label>
//             <Input
//               id="schedule"
//               name="schedule"
//               value={formData.schedule}
//               onChange={handleChange}
//               disabled={submitting}
//             />
//           </div>
//           <div className="space-y-4">
//             <div className="flex justify-between items-center">
//               <Label>Committee Members *</Label>
//               <Button
//                 type="button"
//                 onClick={handleAddMember}
//                 variant="outline"
//                 className="flex items-center gap-2"
//                 disabled={submitting}
//               >
//                 <Plus className="h-4 w-4" />
//                 Add Member
//               </Button>
//             </div>
//             <div className="space-y-4">
//               {formData.members.map((member, index) => (
//                 <div key={`member-${index}`} className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 border rounded-lg relative">
//                   <div>
//                     <Label htmlFor={`employee-id-${index}`}>Employee ID *</Label>
//                     <Input
//                       id={`employee-id-${index}`}
//                       value={member.employeeId}
//                       onChange={(e) => handleUpdateMember(index, "employeeId", e.target.value)}
//                       placeholder="Enter ID (e.g., NTC001)"
//                       required
//                       disabled={submitting}
//                     />
//                   </div>
//                   <div>
//                     <Label htmlFor={`name-${index}`}>Name *</Label>
//                     <Input
//                       id={`name-${index}`}
//                       value={member.name}
//                       onChange={(e) => handleUpdateMember(index, "name", e.target.value)}
//                       placeholder="Full name"
//                       required
//                       disabled={submitting}
//                     />
//                   </div>
//                   <div>
//                     <Label htmlFor={`email-${index}`}>Email *</Label>
//                     <Input
//                       id={`email-${index}`}
//                       type="email"
//                       value={member.email}
//                       onChange={(e) => handleUpdateMember(index, "email", e.target.value)}
//                       placeholder="email@example.com"
//                       required
//                       disabled={submitting}
//                     />
//                   </div>
//                   <div>
//                     <Label htmlFor={`role-${index}`}>Role *</Label>
//                     <select
//                       id={`role-${index}`}
//                       value={member.role}
//                       onChange={(e) => handleUpdateMember(index, "role", e.target.value)}
//                       className="w-full h-10 px-3 py-2 text-base rounded-md border border-input bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
//                       disabled={submitting}
//                     >
//                       <option value="member">Member</option>
//                       <option value="chairperson">Chairperson</option>
//                       <option value="secretary">Secretary</option>
//                     </select>
//                   </div>
//                   <Button
//                     type="button"
//                     variant="ghost"
//                     size="icon"
//                     className="absolute -right-2 -top-2"
//                     onClick={() => handleRemoveMember(index)}
//                     disabled={submitting}
//                   >
//                     <X className="h-4 w-4" />
//                   </Button>
//                 </div>
//               ))}
//               {formData.members.length === 0 && (
//                 <div className="text-center py-8 text-muted-foreground">
//                   No members added yet. Click "Add Member" to begin.
//                 </div>
//               )}
//             </div>
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="formation_letter">Formation Letter</Label>
//             <Input
//               id="formation_letter"
//               name="formation_letter"
//               type="file"
//               accept=".pdf,.doc,.docx"
//               onChange={handleFileChange}
//               disabled={submitting}
//             />
//             {committee.formationLetterURL && (
//               <p className="text-sm text-gray-600">
//                 Current file: {committee.formationLetterURL.split("/").pop() || "Formation Letter"}
//               </p>
//             )}
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="should_notify">Notify Members</Label>
//             <input
//               id="should_notify"
//               type="checkbox"
//               checked={formData.should_notify}
//               onChange={(e) => setFormData((prev) => ({ ...prev, should_notify: e.target.checked }))}
//               disabled={submitting}
//             />
//           </div>
//           <div className="flex justify-end space-x-4">
//             <Button
//               type="button"
//               variant="outline"
//               onClick={() => navigate("/committees")}
//               disabled={submitting}
//             >
//               Cancel
//             </Button>
//             <Button type="submit" disabled={submitting}>
//               {submitting ? (
//                 <>
//                   <Loader2 className="h-4 w-4 animate-spin mr-2" />
//                   Updating...
//                 </>
//               ) : (
//                 "Save Changes"
//               )}
//             </Button>
//           </div>
//         </form>
//       </CardContent>
//     </Card>
//   );
// };

// export default CommitteeUpdate;

// // CommitteeUpdate.tsx
// import { useState, useEffect } from "react";
// import { useParams, useNavigate } from "react-router-dom";
// import {
//   Card,
//   CardContent,
//   CardHeader,
//   CardTitle,
// } from "@/components/ui/card";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import { Label } from "@/components/ui/label";
// import { Textarea } from "@/components/ui/textarea";
// import { Loader2, Plus, X, Check, ChevronsUpDown } from "lucide-react";
// import { useAuth } from "@/contexts/AuthContext";
// import { useToast } from "@/hooks/use-toast";
// import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
// import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
// import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command";
// import { cn } from "@/lib/utils";
// import type { Committee, CommitteeMember } from "@/types/committee";

// interface Employee {
//   _id: string;
//   name: string;
//   employeeId: string;
//   department: string;
//   email?: string;
//   phone?: string;
//   designation?: string;
// }

// interface Member {
//   employeeId: string;
//   name: string;
//   email: string;
//   role: string;
//   department?: string;
//   phone?: string;
//   designation?: string;
// }

// const CommitteeUpdate = () => {
//   const { committeeId } = useParams<{ committeeId: string }>();
//   const navigate = useNavigate();
//   const { hasPermission, token, employees } = useAuth();
//   const { toast } = useToast();

//   const [committee, setCommittee] = useState<Committee | null>(null);
//   const [procurementPlans, setProcurementPlans] = useState<{ id: number; project_name: string }[]>([]);
//   const [selectedProcurementPlan, setSelectedProcurementPlan] = useState<string | null>(null);
//   const [open, setOpen] = useState(false);
//   const [searchInput, setSearchInput] = useState("");
//   const [formData, setFormData] = useState({
//     name: "",
//     purpose: "",
//     committee_type: "",
//     formation_date: "",
//     specification_submission_date: "",
//     review_date: "",
//     schedule: "",
//     members: [] as Member[],
//     formation_letter: null as File | null,
//     should_notify: false,
//   });
//   const [loading, setLoading] = useState(true);
//   const [submitting, setSubmitting] = useState(false);

//   const filteredProcurementPlans = procurementPlans.filter((plan) =>
//     plan.project_name.toLowerCase().includes(searchInput.toLowerCase())
//   );

//   useEffect(() => {
//     if (!hasPermission("manage_committees")) {
//       toast({
//         title: "Access Denied",
//         description: "You do not have permission to edit committees.",
//         variant: "destructive",
//       });
//       navigate("/");
//       return;
//     }

//     const fetchProcurementPlans = async () => {
//       try {
//         const response = await fetch("${import.meta.env.VITE_API_BASE_URL}/api/procurement/plans/", {
//           headers: {
//             Authorization: `Bearer ${token}`,
//           },
//         });
//         if (!response.ok) throw new Error("Failed to fetch procurement plans");
//         const responseData = await response.json();
//         setProcurementPlans(responseData || []);
//       } catch (error) {
//         console.error("Error fetching procurement plans:", error);
//         toast({
//           title: "Error",
//           description: "Failed to load procurement plans",
//           variant: "destructive",
//         });
//       }
//     };

//     const fetchCommittee = async () => {
//       if (!committeeId || !token) return;

//       try {
//         const response = await fetch(
//           `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/`,
//           {
//             headers: {
//               Authorization: `Bearer ${token}`,
//             },
//           }
//         );

//         if (!response.ok) {
//           throw new Error(`Failed to fetch committee: ${response.status} ${response.statusText}`);
//         }

//         const data = await response.json();
//         console.log("Raw API response:", JSON.stringify(data, null, 2));

//         const committeeData = data.data?.committee || data;

//         const formatDate = (date: string | null | undefined): string => {
//           if (!date) return "";
//           let parsedDate: Date;
//           if (date.includes("/")) {
//             const [month, day, year] = date.split("/").map(Number);
//             parsedDate = new Date(year, month - 1, day);
//           } else {
//             parsedDate = new Date(date);
//           }
//           return isNaN(parsedDate.getTime()) ? "" : parsedDate.toISOString().split("T")[0];
//         };

//         const members = Array.isArray(committeeData.membersList)
//           ? committeeData.membersList.map((m: any) => ({
//               employeeId: m.employeeId || "",
//               name: m.name || "",
//               email: m.email || "",
//               role: m.role || "member",
//               department: m.department || "",
//               phone: m.phone || "",
//               designation: m.designation || "",
//             })).filter((m: Member) => m.employeeId)
//           : [];

//         setCommittee(committeeData);
//         setSelectedProcurementPlan(committeeData.procurement_plan?.toString() || null);
//         setFormData({
//           name: committeeData.name || "",
//           purpose: committeeData.purpose || "",
//           committee_type: committeeData.committee_type || "",
//           formation_date: formatDate(committeeData.formation_date),
//           specification_submission_date: formatDate(committeeData.specification_submission_date),
//           review_date: formatDate(committeeData.review_date),
//           schedule: committeeData.schedule || "",
//           members,
//           formation_letter: null,
//           should_notify: false,
//         });

//         if (committeeData.formationLetterURL) {
//           try {
//             const fileResponse = await fetch(
//               `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/download/${committeeId}/`,
//               {
//                 headers: { Authorization: `Bearer ${token}` },
//               }
//             );
//             const blob = await fileResponse.blob();
//             const file = new File(
//               [blob],
//               committeeData.formationLetterURL.split("/").pop() || "formation_letter.pdf",
//               { type: blob.type }
//             );
//             setFormData((prev) => ({ ...prev, formation_letter: file }));
//           } catch (error) {
//             console.error("Error fetching file:", error);
//           }
//         }
//       } catch (error) {
//         console.error("Error fetching committee:", error);
//         toast({
//           title: "Error",
//           description: error instanceof Error ? error.message : "Failed to load committee data",
//           variant: "destructive",
//         });
//         navigate("/");
//       } finally {
//         setLoading(false);
//       }
//     };

//     fetchProcurementPlans();
//     fetchCommittee();
//   }, [committeeId, token, hasPermission, navigate, toast]);

//   const handleChange = (
//     e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
//   ) => {
//     const { name, value } = e.target;
//     setFormData((prev) => ({ ...prev, [name]: value }));
//   };

//   const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
//     const file = e.target.files?.[0] || null;
//     setFormData((prev) => ({ ...prev, formation_letter: file }));
//   };

//   const handleAddMember = async () => {
//     const response = await fetch("${import.meta.env.VITE_API_BASE_URL}/api/users/users/", {
//       headers: { Authorization: `Bearer ${token}` },
//     });
//     const data = await response.json();
//     const availableEmployees = data?.data?.users || [];
//     setFormData((prev) => ({
//       ...prev,
//       members: [
//         ...prev.members,
//         {
//           employeeId: "",
//           name: "",
//           email: "",
//           role: "member",
//           department: "",
//           phone: "",
//           designation: "",
//         },
//       ],
//     }));
//   };

//   const handleUpdateMember = (index: number, field: keyof Member, value: string) => {
//     setFormData((prev) => ({
//       ...prev,
//       members: prev.members.map((m, i) =>
//         i === index ? { ...m, [field]: value } : m
//       ),
//     }));
//   };

//   const handleRemoveMember = async (index: number) => {
//     const member = formData.members[index];
//     if (member.employeeId) {
//       try {
//         const response = await fetch(
//           `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/`,
//           {
//             headers: {
//               Authorization: `Bearer ${token}`,
//             },
//           }
//         );
//         if (!response.ok) {
//           throw new Error(`Committee with ID ${committeeId} not found`);
//         }

//         const committeeData = await response.json();
//         const membersList = committeeData.data?.committee?.membersList || [];
//         const memberExists = membersList.some((m: any) => m.employeeId === member.employeeId);
//         if (!memberExists) {
//           throw new Error(`Employee ${member.employeeId} is not a member of this committee`);
//         }

//         const deleteResponse = await fetch(
//           `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/members/${member.employeeId}/`,
//           {
//             method: "DELETE",
//             headers: {
//               Authorization: `Bearer ${token}`,
//             },
//           }
//         );

//         if (!deleteResponse.ok) {
//           const errorData = await deleteResponse.json().catch(() => ({}));
//           const errorMessage = errorData.message || errorData.error?.message || `Failed to remove member: ${deleteResponse.status}`;
//           throw new Error(errorMessage);
//         }
//       } catch (error) {
//         console.error("Error removing member:", error);
//         toast({
//           title: "Error",
//           description: error instanceof Error ? error.message : "Failed to remove member",
//           variant: "destructive",
//         });
//         return;
//       }
//     }
//     setFormData((prev) => ({
//       ...prev,
//       members: prev.members.filter((_, i) => i !== index),
//     }));
//     toast({
//       title: "Member Removed",
//       description: "Committee member has been removed successfully.",
//     });
//   };

//   const fetchEmployeeData = async (index: number, employeeId: string) => {
//     try {
//       const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/users/employee/${employeeId}/`, {
//         headers: { Authorization: `Bearer ${token}` },
//       });
//       if (!response.ok) throw new Error("Employee not found");
//       const { data: { user } } = await response.json();
//       setFormData((prev) => ({
//         ...prev,
//         members: prev.members.map((m, i) =>
//           i === index
//             ? {
//                 ...m,
//                 name: user.name || "",
//                 email: user.email || "",
//                 department: user.department || "",
//                 phone: user.phoneNumber || "",
//                 designation: user.designation || "",
//               }
//             : m
//         ),
//       }));
//       toast({
//         title: "Employee Data Loaded",
//         description: `${user.name}'s information has been auto-filled`,
//       });
//     } catch (error) {
//       console.error("Error fetching employee data:", error);
//       toast({
//         title: "Error",
//         description: `No record found for ID: ${employeeId}`,
//         variant: "destructive",
//       });
//     }
//   };

//   const handleSubmit = async (e: React.FormEvent) => {
//     e.preventDefault();
//     if (!committeeId) return;

//     if (!formData.name || !formData.purpose || !formData.committee_type) {
//       toast({
//         title: "Validation Error",
//         description: "Name, purpose, and committee type are required",
//         variant: "destructive",
//       });
//       return;
//     }

//     if (formData.members.length === 0) {
//       toast({
//         title: "Validation Error",
//         description: "At least one member is required",
//         variant: "destructive",
//       });
//       return;
//     }

//     const invalidMembers = formData.members.filter(
//       (m) => !m.employeeId || !m.name || !m.email
//     );
//     if (invalidMembers.length > 0) {
//       toast({
//         title: "Validation Error",
//         description: "All members must have Employee ID, Name, and Email",
//         variant: "destructive",
//       });
//       return;
//     }

//     const employeeIds = formData.members.map((m) => m.employeeId);
//     if (new Set(employeeIds).size !== employeeIds.length) {
//       toast({
//         title: "Validation Error",
//         description: "Duplicate employee IDs are not allowed",
//         variant: "destructive",
//       });
//       return;
//     }

//     setSubmitting(true);

//     const formDataToSend = new FormData();
//     formDataToSend.append("name", formData.name);
//     formDataToSend.append("purpose", formData.purpose);
//     formDataToSend.append("committee_type", formData.committee_type);
//     if (selectedProcurementPlan && selectedProcurementPlan !== "none") {
//       formDataToSend.append("procurement_plan", selectedProcurementPlan);
//     }
//     if (formData.formation_date) {
//       formDataToSend.append("formation_date", formData.formation_date);
//     }
//     if (formData.specification_submission_date) {
//       formDataToSend.append("specification_submission_date", formData.specification_submission_date);
//     }
//     if (formData.review_date) {
//       formDataToSend.append("review_date", formData.review_date);
//     }
//     if (formData.schedule) {
//       formDataToSend.append("schedule", formData.schedule);
//     }
//     const membersData = formData.members.map((m) => ({
//       employeeId: m.employeeId,
//       role: m.role || "member",
//     }));
//     formDataToSend.append("members", JSON.stringify(membersData));
//     formDataToSend.append("should_notify", String(formData.should_notify));
//     if (formData.formation_letter) {
//       formDataToSend.append("formation_letter", formData.formation_letter);
//     }

//     try {
//       const response = await fetch(
//         `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/update/${committeeId}/`,
//         {
//           method: "PATCH",
//           headers: {
//             Authorization: `Bearer ${token}`,
//           },
//           body: formDataToSend,
//         }
//       );

//       const data = await response.json();
//       if (!response.ok) {
//         throw new Error(data.message || `Failed to update committee: ${response.status}`);
//       }

//       toast({
//         title: "Update Successful",
//         description: "Committee has been updated.",
//       });
//       navigate("/committees");
//     } catch (error) {
//       console.error("Error updating committee:", error);
//       toast({
//         title: "Update Failed",
//         description: error instanceof Error ? error.message : "Failed to update committee",
//         variant: "destructive",
//       });
//     } finally {
//       setSubmitting(false);
//     }
//   };

//   if (loading || !committee) {
//     return (
//       <div className="flex justify-center items-center h-64">
//         <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
//         <span className="ml-2 text-gray-600">Loading...</span>
//       </div>
//     );
//   }

//   return (
//     <Card className="max-w-3xl mx-auto mt-8">
//       <CardHeader>
//         <CardTitle>Edit Committee</CardTitle>
//       </CardHeader>
//       <CardContent>
//         <form onSubmit={handleSubmit} className="space-y-6">
//           <div className="space-y-2">
//             <Label htmlFor="name">Committee Name *</Label>
//             <Input
//               id="name"
//               name="name"
//               value={formData.name}
//               onChange={handleChange}
//               required
//               disabled={submitting}
//             />
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="purpose">Purpose *</Label>
//             <Textarea
//               id="purpose"
//               name="purpose"
//               value={formData.purpose}
//               onChange={handleChange}
//               required
//               disabled={submitting}
//             />
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="committee_type">Committee Type *</Label>
//             <Select
//               value={formData.committee_type}
//               onValueChange={(value) =>
//                 setFormData((prev) => ({ ...prev, committee_type: value }))
//               }
//               disabled={submitting}
//             >
//               <SelectTrigger>
//                 <SelectValue placeholder="Select committee type" />
//               </SelectTrigger>
//               <SelectContent>
//                 <SelectItem value="specification">Specification</SelectItem>
//                 <SelectItem value="evaluation">Evaluation</SelectItem>
//                 <SelectItem value="other">Other</SelectItem>
//               </SelectContent>
//             </Select>
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="procurement_plan">Procurement Plan</Label>
//             <Popover open={open} onOpenChange={setOpen}>
//               <PopoverTrigger asChild>
//                 <Button
//                   variant="outline"
//                   role="combobox"
//                   aria-expanded={open}
//                   className="w-full justify-between"
//                   disabled={submitting}
//                 >
//                   {selectedProcurementPlan
//                     ? procurementPlans.find((plan) => plan.id.toString() === selectedProcurementPlan)?.project_name ||
//                       "Select procurement plan"
//                     : "Select procurement plan"}
//                   <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
//                 </Button>
//               </PopoverTrigger>
//               <PopoverContent className="w-full p-0">
//                 <Command>
//                   <CommandInput
//                     placeholder="Search procurement plan..."
//                     onValueChange={(value) => setSearchInput(typeof value === 'string' ? value : "")}
//                   />
//                   <CommandEmpty>No procurement plan found.</CommandEmpty>
//                   <CommandGroup>
//                     <CommandItem
//                       value="none"
//                       onSelect={() => {
//                         setSelectedProcurementPlan(null);
//                         setOpen(false);
//                       }}
//                     >
//                       <Check
//                         className={cn(
//                           "mr-2 h-4 w-4",
//                           selectedProcurementPlan === null ? "opacity-100" : "opacity-0"
//                         )}
//                       />
//                       None
//                     </CommandItem>
//                     {filteredProcurementPlans.map((plan) => (
//                       <CommandItem
//                         key={plan.id}
//                         value={plan.project_name}
//                         onSelect={() => {
//                           setSelectedProcurementPlan(plan.id.toString());
//                           setOpen(false);
//                         }}
//                       >
//                         <Check
//                           className={cn(
//                             "mr-2 h-4 w-4",
//                             selectedProcurementPlan === plan.id.toString() ? "opacity-100" : "opacity-0"
//                           )}
//                         />
//                         {plan.project_name}
//                       </CommandItem>
//                     ))}
//                   </CommandGroup>
//                 </Command>
//               </PopoverContent>
//             </Popover>
//           </div>
//           <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
//             <div className="space-y-2">
//               <Label htmlFor="formation_date">Formation Date *</Label>
//               <Input
//                 id="formation_date"
//                 name="formation_date"
//                 type="date"
//                 value={formData.formation_date}
//                 onChange={handleChange}
//                 required
//                 disabled={submitting}
//               />
//             </div>
//             <div className="space-y-2">
//               <Label htmlFor="specification_submission_date">Specification Submission Date</Label>
//               <Input
//                 id="specification_submission_date"
//                 name="specification_submission_date"
//                 type="date"
//                 value={formData.specification_submission_date}
//                 onChange={handleChange}
//                 disabled={submitting}
//               />
//             </div>
//             <div className="space-y-2">
//               <Label htmlFor="review_date">Review Date</Label>
//               <Input
//                 id="review_date"
//                 name="review_date"
//                 type="date"
//                 value={formData.review_date}
//                 onChange={handleChange}
//                 disabled={submitting}
//               />
//             </div>
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="schedule">Schedule</Label>
//             <Input
//               id="schedule"
//               name="schedule"
//               value={formData.schedule}
//               onChange={handleChange}
//               disabled={submitting}
//             />
//           </div>
//           <div className="space-y-4">
//             <div className="flex justify-between items-center">
//               <Label>Committee Members *</Label>
//               <Button
//                 type="button"
//                 onClick={handleAddMember}
//                 variant="outline"
//                 className="flex items-center gap-2"
//                 disabled={submitting}
//               >
//                 <Plus className="h-4 w-4" />
//                 Add Member
//               </Button>
//             </div>
//             <div className="space-y-4">
//               {formData.members.map((member, index) => (
//                 <div key={`member-${index}`} className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 border rounded-lg relative">
//                   <div>
//                     <Label htmlFor={`employee-id-${index}`}>Employee ID *</Label>
//                     <Input
//                       id={`employee-id-${index}`}
//                       value={member.employeeId}
//                       onChange={(e) => {
//                         handleUpdateMember(index, "employeeId", e.target.value);
//                         if (e.target.value.length >= 6) {
//                           fetchEmployeeData(index, e.target.value);
//                         }
//                       }}
//                       placeholder="Enter ID (e.g., NTC001)"
//                       required
//                       disabled={submitting}
//                     />
//                   </div>
//                   <div>
//                     <Label htmlFor={`name-${index}`}>Name *</Label>
//                     <Input
//                       id={`name-${index}`}
//                       value={member.name}
//                       onChange={(e) => handleUpdateMember(index, "name", e.target.value)}
//                       placeholder="Full name"
//                       required
//                       disabled={submitting}
//                     />
//                   </div>
//                   <div>
//                     <Label htmlFor={`email-${index}`}>Email *</Label>
//                     <Input
//                       id={`email-${index}`}
//                       type="email"
//                       value={member.email}
//                       onChange={(e) => handleUpdateMember(index, "email", e.target.value)}
//                       placeholder="email@example.com"
//                       required
//                       disabled={submitting}
//                     />
//                   </div>
//                   <div>
//                     <Label htmlFor={`role-${index}`}>Role *</Label>
//                     <select
//                       id={`role-${index}`}
//                       value={member.role}
//                       onChange={(e) => handleUpdateMember(index, "role", e.target.value)}
//                       className="w-full h-10 px-3 py-2 text-base rounded-md border border-input bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
//                       disabled={submitting}
//                     >
//                       <option value="member">Member</option>
//                       <option value="chairperson">Chairperson</option>
//                       <option value="secretary">Secretary</option>
//                     </select>
//                   </div>
//                   <Button
//                     type="button"
//                     variant="ghost"
//                     size="icon"
//                     className="absolute -right-2 -top-2"
//                     onClick={() => handleRemoveMember(index)}
//                     disabled={submitting}
//                   >
//                     <X className="h-4 w-4" />
//                   </Button>
//                 </div>
//               ))}
//               {formData.members.length === 0 && (
//                 <div className="text-center py-8 text-muted-foreground">
//                   No members added yet. Click "Add Member" to begin.
//                 </div>
//               )}
//             </div>
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="formation_letter">Formation Letter</Label>
//             <Input
//               id="formation_letter"
//               name="formation_letter"
//               type="file"
//               accept=".pdf,.doc,.docx"
//               onChange={handleFileChange}
//               disabled={submitting}
//             />
//             {committee.formationLetterURL && (
//               <p className="text-sm text-gray-600">
//                 Current file: {committee.formationLetterURL.split("/").pop() || "Formation Letter"}
//               </p>
//             )}
//           </div>
//           <div className="space-y-2">
//             <Label htmlFor="should_notify">Notify Members</Label>
//             <input
//               id="should_notify"
//               type="checkbox"
//               checked={formData.should_notify}
//               onChange={(e) => setFormData((prev) => ({ ...prev, should_notify: e.target.checked }))}
//               disabled={submitting}
//             />
//           </div>
//           <div className="flex justify-end space-x-4">
//             <Button
//               type="button"
//               variant="outline"
//               onClick={() => navigate("/committees")}
//               disabled={submitting}
//             >
//               Cancel
//             </Button>
//             <Button type="submit" disabled={submitting}>
//               {submitting ? (
//                 <>
//                   <Loader2 className="h-4 w-4 animate-spin mr-2" />
//                   Updating...
//                 </>
//               ) : (
//                 "Save Changes"
//               )}
//             </Button>
//           </div>
//         </form>
//       </CardContent>
//     </Card>
//   );
// };

// export default CommitteeUpdate;
