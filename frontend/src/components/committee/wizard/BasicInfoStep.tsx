import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { useDebounce } from "@/hooks/useDebounce";
import { useGetProcurementPlans } from "@/hooks/useProcurementPlan";
import { cn } from "@/lib/utils";
import { ProcurementPlan } from "@/types/procurement-plan";
import { AlertCircle, Building, Check, FileText, Loader2, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

interface BasicInfoStepProps {
  name: string;
  purpose: string;
  committeeType: string;
  selectedProcurementPlan: string | null;
  onNameChange: (value: string) => void;
  onPurposeChange: (value: string) => void;
  onCommitteeTypeChange: (value: string) => void;
  onProcurementPlanChange: (value: string | null) => void;
  onPlanNameChange: (value: string) => void;
  preSelectedPlan?: ProcurementPlan;
}

const BasicInfoStep = ({
  name,
  purpose,
  committeeType,
  selectedProcurementPlan,
  onNameChange,
  onPurposeChange,
  onCommitteeTypeChange,
  onProcurementPlanChange,
  onPlanNameChange,
  preSelectedPlan,
}: BasicInfoStepProps) => {
  const { token } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");

  // If we have a pre-selected plan, use it directly; otherwise use search
  const shouldSearch = !preSelectedPlan;

  // Debounce search only when we need to search
  const debouncedSearch = useDebounce(shouldSearch ? searchInput : "", 1000);

  // Search API call (only when no pre-selected plan)
  const { data: pPlansResponse, isFetching } = useGetProcurementPlans(shouldSearch ? debouncedSearch : "", 1, 10);

  // Use pre-selected plan or search results
  const procurementPlans: ProcurementPlan[] = preSelectedPlan
    ? [preSelectedPlan]
    : (pPlansResponse?.data || []).reduce((unique: ProcurementPlan[], plan) => {
      const isDuplicate = unique.some(
        (existingPlan) =>
          existingPlan.id === plan.id ||
          (existingPlan.project_name === plan.project_name && existingPlan.department === plan.department)
      );
      if (!isDuplicate) {
        unique.push(plan);
      }
      return unique;
    }, []);

  // Check if plan is pre-selected
  const isPreSelected = Boolean(preSelectedPlan);

  // Find the selected plan
  const selectedPlan =
    preSelectedPlan || procurementPlans.find((plan) => plan.id.toString() === selectedProcurementPlan);

  useEffect(() => {
    if (selectedPlan) {
      onPlanNameChange(selectedPlan.project_name);
    }
    console.log("Procurement Plans Debug:", {
      preSelectedPlan: preSelectedPlan?.project_name,
      shouldSearch,
      isFetching,
      searchQuery: debouncedSearch,
      selectedPlan: selectedPlan?.project_name,
      totalPlans: procurementPlans.length,
    });
  }, [
    selectedPlan,
    preSelectedPlan?.project_name,
    shouldSearch,
    isFetching,
    debouncedSearch,
    procurementPlans.length,
    onPlanNameChange,
  ]);

  return (
    <div className="space-y-6">
      {/* Procurement Plan Selection - Required Field */}
      <div className="space-y-4">
        <div className="space-y-2">
          <Label className="text-base font-medium flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Procurement Plan <span className="text-destructive">*</span>
          </Label>
          <p className="text-sm text-muted-foreground">Select a procurement plan to associate with this committee</p>
        </div>

        {/* Conditional rendering: Pre-selected vs Search Interface */}
        {preSelectedPlan ? (
          /* Pre-selected Plan Display - No search, no edit */
          <div className="space-y-3">
            <Card className="border-primary bg-primary/5">
              <CardContent className="p-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <FileText className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-medium text-sm truncate" title={preSelectedPlan.project_name}>
                        {preSelectedPlan.project_name}
                      </h4>
                      <Badge variant="default" className="text-xs">
                        Pre-selected
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="text-xs">
                        <Building className="h-3 w-3 mr-1" />
                        {preSelectedPlan.department}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        {preSelectedPlan.fiscal_year}
                      </Badge>
                      {preSelectedPlan.budget && (
                        <Badge variant="outline" className="text-xs">
                          NPR {preSelectedPlan.budget.toLocaleString()}
                        </Badge>
                      )}
                    </div>
                    {preSelectedPlan.project_description && (
                      <p
                        className="text-xs text-muted-foreground line-clamp-2"
                        title={preSelectedPlan.project_description}
                      >
                        {preSelectedPlan.project_description}
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          /* Search Interface for manual selection */
          <div className="space-y-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Type to search procurement plans..."
                value={searchInput}
                onChange={(e) => {
                  setSearchInput(e.target.value);
                  setOpen(true);
                }}
                className="pl-9 pr-10 h-11"
                onFocus={() => setOpen(true)}
                onBlur={(e) => {
                  // Delay closing to allow clicking on options
                  setTimeout(() => {
                    if (!e.relatedTarget?.closest("[data-search-results]")) {
                      setOpen(false);
                    }
                  }, 150);
                }}
              />
              {isFetching && (
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              )}
              {searchInput && !isFetching && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 h-7 w-7 p-0 hover:bg-muted"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSearchInput("");
                    setOpen(false);
                  }}
                >
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>

            {/* Search Results Dropdown */}
            {open && (
              <div className="relative" data-search-results>
                <div className="absolute top-0 left-0 right-0 z-50 bg-white border rounded-lg shadow-lg">
                  <div className="max-h-80 overflow-y-auto">
                    {isFetching ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="flex flex-col items-center gap-3 text-muted-foreground">
                          <Loader2 className="h-6 w-6 animate-spin" />
                          <div className="text-center">
                            <p className="text-sm font-medium">Searching procurement plans...</p>
                            <p className="text-xs">Please wait while we find matching plans</p>
                          </div>
                        </div>
                      </div>
                    ) : procurementPlans.length === 0 ? (
                      <div className="flex items-center justify-center py-8">
                        <div className="text-center text-muted-foreground max-w-sm">
                          <FileText className="h-12 w-12 mx-auto mb-3 opacity-40" />
                          <p className="text-sm font-medium mb-1">
                            {debouncedSearch ? "No plans found" : "Start typing to search"}
                          </p>
                          <p className="text-xs">
                            {debouncedSearch
                              ? `No procurement plans match "${debouncedSearch}". Try different keywords.`
                              : "Enter project name, department, or fiscal year to find plans"}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="divide-y">
                        {procurementPlans.map((plan, index) => (
                          <div
                            key={plan.id}
                            className={cn(
                              "flex items-start gap-3 p-4 cursor-pointer hover:bg-muted/50 transition-colors",
                              selectedProcurementPlan === plan.id.toString() &&
                              "bg-primary/5 border-l-4 border-l-primary",
                              index === 0 && "rounded-t-lg",
                              index === procurementPlans.length - 1 && "rounded-b-lg"
                            )}
                            onMouseDown={(e) => e.preventDefault()} // Prevent input blur
                            onClick={() => {
                              onProcurementPlanChange(plan.id.toString());
                              onPlanNameChange(plan.project_name);
                              setSearchInput(plan.project_name);
                              setOpen(false);
                            }}
                          >
                            <div
                              className={cn(
                                "w-5 h-5 rounded-full border-2 flex items-center justify-center mt-1 flex-shrink-0 transition-colors",
                                selectedProcurementPlan === plan.id.toString()
                                  ? "border-primary bg-primary"
                                  : "border-muted-foreground hover:border-primary"
                              )}
                            >
                              {selectedProcurementPlan === plan.id.toString() && (
                                <Check className="w-3 h-3 text-white" />
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-start justify-between mb-2">
                                <h4 className="font-semibold text-sm leading-tight" title={plan.project_name}>
                                  {plan.project_name}
                                </h4>
                                {selectedProcurementPlan === plan.id.toString() && (
                                  <Badge variant="default" className="text-xs ml-2 flex-shrink-0">
                                    Selected
                                  </Badge>
                                )}
                              </div>
                              <div className="flex flex-wrap items-center gap-1.5 mb-2">
                                <Badge variant="outline" className="text-xs">
                                  <Building className="h-3 w-3 mr-1" />
                                  {plan.department}
                                </Badge>
                                <Badge variant="secondary" className="text-xs">
                                  FY {plan.fiscal_year}
                                </Badge>
                                {plan.budget && (
                                  <Badge
                                    variant="outline"
                                    className="text-xs text-green-700 bg-green-50 border-green-200"
                                  >
                                    NPR {plan.budget.toLocaleString()}
                                  </Badge>
                                )}
                              </div>
                              {plan.project_description && (
                                <p
                                  className="text-xs text-muted-foreground line-clamp-2 leading-relaxed"
                                  title={plan.project_description}
                                >
                                  {plan.project_description}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  {procurementPlans.length > 0 && !isFetching && (
                    <div className="p-3 bg-muted/30 border-t text-xs text-muted-foreground text-center">
                      {procurementPlans.length} plan{procurementPlans.length !== 1 ? "s" : ""} found
                      {debouncedSearch && ` for "${debouncedSearch}"`}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Selected Plan Display */}
            {selectedPlan && (
              <Card className="border-primary bg-primary/5">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <FileText className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <h4 className="font-medium text-sm truncate" title={selectedPlan.project_name}>
                            {selectedPlan.project_name}
                          </h4>
                          <Badge variant="default" className="text-xs">
                            Selected
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline" className="text-xs">
                            <Building className="h-3 w-3 mr-1" />
                            {selectedPlan.department}
                          </Badge>
                          <Badge variant="secondary" className="text-xs">
                            {selectedPlan.fiscal_year}
                          </Badge>
                          {selectedPlan.budget && (
                            <Badge variant="outline" className="text-xs">
                              NPR {selectedPlan.budget.toLocaleString()}
                            </Badge>
                          )}
                        </div>
                        {selectedPlan.project_description && (
                          <p
                            className="text-xs text-muted-foreground line-clamp-2"
                            title={selectedPlan.project_description}
                          >
                            {selectedPlan.project_description}
                          </p>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 flex-shrink-0"
                      onClick={() => {
                        onProcurementPlanChange(null);
                        setSearchInput("");
                      }}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
            {/* Enhanced Error State */}
            {!isPreSelected && !selectedProcurementPlan && !searchInput && (
              <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-red-800">Procurement plan required</p>
                  <p className="text-xs text-red-600 mt-1">
                    Select a procurement plan to continue with committee creation.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label htmlFor="committee-name" className="text-[11px] font-bold text-slate-400 tracking-wider">
            Committee Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="committee-name"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="Enter Committee Name"
            className={cn("h-11", name.length > 0 && name.length < 3 ? "border-destructive" : "border-slate-200 focus:border-[hsl(209,100%,32%)]")}
          />
          {name.length > 0 && name.length < 3 && (
            <p className="text-sm text-destructive">Committee name must be at least 3 characters</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="committee-type" className="text-[11px] font-bold text-slate-400 tracking-wider">
            Committee Type <span className="text-destructive">*</span>
          </Label>
          <Select value={committeeType} onValueChange={onCommitteeTypeChange}>
            <SelectTrigger className="h-11 border-slate-200 focus:ring-[hsl(209,100%,32%)]">
              <SelectValue placeholder="Select committee type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="specification">Specification Committee</SelectItem>
              <SelectItem value="evaluation">Evaluation Committee</SelectItem>
              <SelectItem value="review">Review Committee</SelectItem>
              <SelectItem value="contract">Contract Committee</SelectItem>

              <SelectItem value="other">Other</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="committee-purpose" className="text-[11px] font-bold text-slate-400 tracking-wider">
          Purpose & Objectives <span className="text-destructive">*</span>
        </Label>
        <Textarea
          id="committee-purpose"
          value={purpose}
          onChange={(e) => onPurposeChange(e.target.value)}
          placeholder="Describe the committee's purpose and objectives"
          rows={4}
          className={cn(purpose.length > 0 && purpose.length < 10 ? "border-destructive" : "border-slate-200 focus:border-[hsl(209,100%,32%)]")}
        />
        {purpose.length > 0 && purpose.length < 10 && (
          <p className="text-sm text-destructive">Purpose must be at least 10 characters</p>
        )}
      </div>

      <div className="bg-muted/50 p-4 rounded-lg">
        <h4 className="font-medium text-sm mb-2">Step Guidelines</h4>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>
            • <strong>Procurement plan selection is mandatory</strong> - use the search input to find plans
          </li>
          <li>• Search with 1-second debouncing to efficiently find procurement plans</li>
          <li>• Choose a clear, descriptive name for your committee</li>
          <li>• Select the appropriate committee type based on its function</li>
          <li>• Provide a detailed purpose that explains the committee's objectives and responsibilities</li>
        </ul>
      </div>
    </div>
  );
};

export default BasicInfoStep;
