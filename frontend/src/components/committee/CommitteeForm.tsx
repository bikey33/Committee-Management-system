import FormContainer from "./form/FormContainer";
import FormHeader from "./form/FormHeader";
import FormActions from "./form/FormActions";
import BasicInfoFields from "./BasicInfoFields";
import CommitteeMembers from "./CommitteeMembers";
import FileUpload from "./FileUpload";
import { useCommitteeForm } from "@/hooks/useCommitteeForm";
import type { Committee } from "@/types/committee";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext"; // Import AuthContext
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command";
import { Button } from "@/components/ui/button";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { addDays } from "date-fns";

interface CommitteeFormProps {
  onClose: () => void;
  onCreateCommittee?: (committee: Committee) => void;
  committeeId?: string;
}

const CommitteeForm = ({ onClose, onCreateCommittee, committeeId }: CommitteeFormProps) => {

  const navigate = useNavigate();
  const { token } = useAuth(); // Get token from AuthContext
  const [isLoading, setIsLoading] = useState(false);
  const [procurementPlans, setProcurementPlans] = useState<{ id: number; project_name: string }[]>([]);
  const [selectedProcurementPlan, setSelectedProcurementPlan] = useState<string | null>(null);
  const [committeeType, setCommitteeType] = useState<string>("");
  const [open, setOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [deadlineDays, setDeadlineDays] = useState<number>(30);

  const filteredProcurementPlans = procurementPlans.filter((plan) =>
    plan.project_name.toLowerCase().includes(searchInput.toLowerCase())
  );

  const {
    members,
    formDate,
    selectedFile,
    setMembers,
    setFormDate,
    setSelectedFile,
    name,
    purpose,
    handleAddMember,
    handleUpdateMember,
    setName,
    setPurpose,
    resetForm,
  } = useCommitteeForm(onClose, onCreateCommittee);

  const deadline = formDate ? addDays(new Date(formDate), deadlineDays) : null;

  useEffect(() => {
    if (!token) {
      console.log("No token found, skipping fetchProcurementPlans");
      return; // Prevent API call if no token exists
    }

    const fetchProcurementPlans = async () => {
      try {
        const url = `${import.meta.env.VITE_API_BASE_URL}/api/procurement/plans/`;
        console.log("Fetching procurement plans from:", url);
        console.log("Token used in request:", token); // Debug log to inspect the token
        const response = await fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        console.log("Response status:", response.status);
        console.log("Response headers:", response.headers.get("content-type"));

        if (!response.ok) {
          const errorText = await response.text();
          console.error("Response error:", response.status, errorText);
          if (response.status === 401) {
            toast.error("Session Expired", {
              description: "Your session has expired. Please log in again.",
            });
            navigate("/login");
            return;
          }
          throw new Error(`Failed to fetch procurement plans: ${response.status} ${response.statusText}`);
        }

        const contentType = response.headers.get("content-type");
        if (!contentType || !contentType.includes("application/json")) {
          const errorText = await response.text();
          console.error("Unexpected response format:", errorText);
          throw new Error("Response is not JSON");
        }

        const responseData = await response.json();
        console.log("Procurement plans response:", responseData);
        setProcurementPlans(responseData || []);
        console.log("Updated procurementPlans state:", responseData || []);
      } catch (error) {
        console.error("Error fetching procurement plans:", error);
        if (error instanceof Error && !error.message.includes("Please log in again")) {
          toast.error("Error", {
            description: "Failed to load procurement plans",
          });
        }
      }
    };
    fetchProcurementPlans();
  }, [toast, navigate, token]);

  useEffect(() => {
    if (!committeeId || !token) return;

    const fetchCommittee = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/`, {
          method: "GET",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          if (response.status === 401) {
            toast.error("Session Expired", {
              description: "Your session has expired. Please log in again.",
            });
            navigate("/login");
            return;
          }
          throw new Error("Failed to fetch committee");
        }

        const { data } = await response.json();

        setName(data.committee.name);
        setPurpose(data.committee.purpose);
        setCommitteeType(data.committee.committee_type);
        setSelectedProcurementPlan(data.committee.procurement_plan?.toString() || null);
        setFormDate(data.committee.formation_date || "");
        setDeadlineDays(30);
        setMembers(
          (data.committee.membersList || []).map((member: any) => ({
            id: member._id,
            employeeId: member.employeeId,
            name: member.name,
            email: member.email,
            office: member.office || "",
            phone: member.phone || "",
            role: member.role || "member",
            tasks: member.tasks || [],
            position: member.position || "",
          }))
        );

        if (data.committee.formationLetterURL) {
          try {
            const fileResponse = await fetch(
              `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/download/`,
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            );
            if (fileResponse.status === 401) {
              toast.error("Session Expired", {
                description: "Your session has expired. Please log in again.",
              });
              navigate("/login");
              return;
            }
            const blob = await fileResponse.blob();
            const file = new File(
              [blob],
              data.committee.formationLetterURL.split("/").pop() || "formation_letter.pdf",
              {
                type: blob.type,
                lastModified: new Date().getTime(),
              }
            );
            setSelectedFile(file);
          } catch (error) {
            console.error("Error fetching file:", error);
            const mockFile = new File(
              [],
              data.committee.formationLetterURL.split("/").pop() || "formation_letter.pdf",
              {
                type: "application/pdf",
              }
            );
            setSelectedFile(mockFile);
          }
        }
      } catch (error) {
        console.error("Error fetching committee:", error);
        if (error instanceof Error && !error.message.includes("Please log in again")) {
          toast.error("Error", {
            description: "Failed to load committee data",
          });
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchCommittee();
  }, [committeeId, toast, setName, setPurpose, setFormDate, setMembers, setSelectedFile, navigate, token]);

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name || !purpose || !committeeType) {
      toast.error("Validation Error", {
        description: "Name, purpose, and committee type are required",
      });
      return;
    }

    if (members.length === 0) {
      toast.error("Validation Error", {
        description: "At least one member is required",
      });
      return;
    }

    const invalidMembers = members.filter((m) => !m.employeeId || !m.name || !m.email);

    if (invalidMembers.length > 0) {
      toast.error("Validation Error", {
        description: "Please complete all required fields (Employee ID, Name, Email) for all members",
      });
      return;
    }

    const employeeIds = members.map((m) => m.employeeId);
    const uniqueEmployeeIds = new Set(employeeIds);
    if (uniqueEmployeeIds.size !== employeeIds.length) {
      toast.error("Validation Error", {
        description: "Duplicate employee IDs are not allowed",
      });
      return;
    }

    try {
      setIsLoading(true);

      if (!token) {
        throw new Error("No authentication token found. Please log in.");
      }

      const formData = new FormData();
      formData.append("name", name);
      formData.append("purpose", purpose);
      formData.append("committee_type", committeeType);
      if (selectedProcurementPlan && selectedProcurementPlan !== "none") {
        formData.append("procurement_plan", selectedProcurementPlan);
      }
      if (formDate) formData.append("formation_date", formDate);
      if (deadline) formData.append("deadline", deadline.toISOString().split("T")[0]);
      formData.append("should_notify", "true");
      const membersData = members.map((m) => ({
        employeeId: m.employeeId,
        role: m.role || "member",
      }));
      formData.append("members", JSON.stringify(membersData));
      if (selectedFile) {
        formData.append("formation_letter", selectedFile);
      }

      const endpoint = committeeId
        ? `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/update/${committeeId}/`
        : `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/create/`;
      const method = committeeId ? "PATCH" : "POST";

      console.log("Submitting:", {
        name,
        purpose,
        committee_type: committeeType,
        procurement_plan: selectedProcurementPlan,
        formation_date: formDate,
        deadline,
        members: membersData,
        should_notify: true,
        hasFile: !!selectedFile,
      });

      const response = await fetch(endpoint, {
        method,
        body: formData,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session Expired", {
            description: "Your session has expired. Please log in again.",
          });
          navigate("/login");
          return;
        }
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to save committee");
      }

      const data = await response.json();

      toast.success("Success", {
        description: committeeId ? "Committee updated successfully" : "Committee created successfully",
      });

      if (onCreateCommittee) {
        onCreateCommittee(data.committee || data);
      }

      if (!committeeId) {
        resetForm();
      }

      onClose();
    } catch (error) {
      console.error("Error saving committee:", error);
      if (error instanceof Error && !error.message.includes("Please log in again")) {
        toast.error("Error", {
          description: error.message || "Failed to save committee",
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveMember = async (index: number) => {
    try {
      if (committeeId && members[index]?.employeeId && token) {
        const response = await fetch(
          `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/remove-member/${committeeId}/${members[index].employeeId
          }/`,
          {
            method: "DELETE",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            toast.error("Session Expired", {
              description: "Your session has expired. Please log in again.",
            });
            navigate("/login");
            return;
          }
          throw new Error("Failed to remove member");
        }

        setMembers(members.filter((_, i) => i !== index));
        toast.success("Member Removed", {
          description: "Committee member has been removed successfully.",
        });
      } else {
        setMembers(members.filter((_, i) => i !== index));
      }
    } catch (error) {
      console.error("Error removing member:", error);
      if (error instanceof Error && !error.message.includes("Please log in again")) {
        toast.error("Error", {
          description: "Failed to remove committee member",
        });
      }
    }
  };

  const downloadFormationLetter = async () => {
    if (!committeeId) return;

    try {
      if (!token) {
        throw new Error("No authentication token found. Please log in.");
      }

      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/committee/committees/${committeeId}/download/`,
        {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Session Expired", {
            description: "Your session has expired. Please log in again.",
          });
          navigate("/login");
          return;
        }
        throw new Error("Failed to download file");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `formation-letter-${committeeId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (error) {
      console.error("Error downloading file:", error);
      if (error instanceof Error && !error.message.includes("Please log in again")) {
        toast.error("Error", {
          description: "Failed to download formation letter",
        });
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-3 backdrop-blur-sm animate-in fade-in duration-300 sm:items-center sm:p-4">
      <div className="w-full max-w-5xl max-h-[95vh] overflow-y-auto rounded-2xl bg-white p-4 shadow-2xl animate-in slide-in-from-bottom-4 duration-300 sm:p-6 lg:p-8">
        <FormHeader onClose={onClose} />

        <form onSubmit={handleFormSubmit} className="mt-6 space-y-8">
          <div className="space-y-6">
            <BasicInfoFields
              name={name}
              purpose={purpose}
              onNameChange={setName}
              onPurposeChange={setPurpose}
              disabled={isLoading}
            />

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Committee Type <span className="text-red-500">*</span>
                </label>
                <Select value={committeeType} onValueChange={setCommitteeType} disabled={isLoading}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select Committee Type" />
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

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Procurement Plan</label>
                <Popover open={open} onOpenChange={setOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={open}
                      className="w-full justify-between"
                      disabled={isLoading}
                    >
                      {selectedProcurementPlan
                        ? procurementPlans.find((plan) => plan.id.toString() === selectedProcurementPlan)?.project_name ||
                        "Select Procurement Plan"
                        : "Select Procurement Plan"}
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[92vw] p-0 sm:w-[420px] lg:w-full lg:min-w-[420px]">
                    <Command>
                      <CommandInput
                        placeholder="Search Procurement Plan..."
                        onValueChange={(value) => setSearchInput(typeof value === "string" ? value : "")}
                      />
                      <CommandEmpty>No Procurement Plan Found.</CommandEmpty>
                      <CommandGroup>
                        <CommandItem
                          value="none"
                          onSelect={() => {
                            setSelectedProcurementPlan(null);
                            setOpen(false);
                          }}
                        >
                          <Check
                            className={cn("mr-2 h-4 w-4", selectedProcurementPlan === null ? "opacity-100" : "opacity-0")}
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
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Formation Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  value={formDate || ""}
                  onChange={(e) => setFormDate(e.target.value)}
                  className="w-full rounded border p-2"
                  disabled={isLoading}
                  required
                />
              </div>
              <div className="mt-1">
                <label className="block text-sm font-medium text-gray-700">Days From Formation Date</label>
                <input
                  type="number"
                  value={deadlineDays}
                  onChange={(e) => setDeadlineDays(Number(e.target.value) || 30)}
                  className="w-full rounded border p-2"
                  min="1"
                  disabled={isLoading}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Deadline (Auto-Calculated)</label>
                <input
                  type="date"
                  value={deadline ? deadline.toISOString().split("T")[0] : ""}
                  className="w-full rounded border bg-gray-100 p-2"
                  disabled
                />
              </div>
            </div>

            <CommitteeMembers
              members={members}
              onAddMember={handleAddMember}
              onUpdateMember={handleUpdateMember}
              onRemoveMember={handleRemoveMember}
              disabled={isLoading}
            />

            <FileUpload
              onFileChange={setSelectedFile}
              existingFile={
                committeeId && selectedFile
                  ? {
                    name: selectedFile.name,
                    size: selectedFile.size,
                    onDownload: downloadFormationLetter,
                  }
                  : undefined
              }
              disabled={isLoading}
            />
          </div>

          <FormActions onClose={onClose} isLoading={isLoading} isEditMode={!!committeeId} />
        </form>
      </div>
    </div>
  );
};

export default CommitteeForm;
