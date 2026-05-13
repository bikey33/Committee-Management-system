import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, FileText, Calendar, DollarSign, Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";

interface ProcurementPlan {
  _id: string;
  title: string;
  description?: string;
  budget?: number;
  plannedDate?: string;
  status?: string;
  department?: string;
}

interface ProcurementPlanSelectorProps {
  value: string | null;
  onSelect: (planId: string | null) => void;
}

const ProcurementPlanSelector = ({ value, onSelect }: ProcurementPlanSelectorProps) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [plans, setPlans] = useState<ProcurementPlan[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<ProcurementPlan | null>(null);
  const { token } = useAuth();


  const searchPlans = async (term: string) => {
    if (term.length < 2) {
      setPlans([]);
      setShowResults(false);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL}/api/procurement/plans/search?q=${encodeURIComponent(term)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setPlans(data.plans || []);
        setShowResults(true);
      } else {
        throw new Error("Failed to fetch procurement plans");
      }
    } catch (error) {
      console.error("Error searching procurement plans:", error);
      toast.error("Search Error", {
        description: "Failed to search procurement plans. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      searchPlans(searchTerm);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm]);

  const handleSelectPlan = (plan: ProcurementPlan) => {
    setSelectedPlan(plan);
    onSelect(plan._id);
    setSearchTerm("");
    setShowResults(false);
    setPlans([]);
  };

  const handleClearSelection = () => {
    setSelectedPlan(null);
    onSelect(null);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="space-y-4">
      {selectedPlan ? (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="w-4 h-4 text-primary" />
                  <h4 className="font-medium">{selectedPlan.title}</h4>
                </div>
                {selectedPlan.description && (
                  <p className="text-sm text-muted-foreground mb-3">
                    {selectedPlan.description}
                  </p>
                )}
                <div className="flex items-center gap-4 text-sm">
                  {selectedPlan.budget && (
                    <div className="flex items-center gap-1">
                      <DollarSign className="w-3 h-3" />
                      <span>{formatCurrency(selectedPlan.budget)}</span>
                    </div>
                  )}
                  {selectedPlan.plannedDate && (
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      <span>{formatDate(selectedPlan.plannedDate)}</span>
                    </div>
                  )}
                  {selectedPlan.status && (
                    <Badge variant="secondary" className="text-xs">
                      {selectedPlan.status}
                    </Badge>
                  )}
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleClearSelection}
              >
                Change
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="relative">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search procurement plans..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
            {isLoading && (
              <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 w-4 h-4 animate-spin text-muted-foreground" />
            )}
          </div>

          {showResults && (
            <Card className="absolute top-full left-0 right-0 z-50 mt-1 max-h-60 overflow-y-auto">
              <CardContent className="p-2">
                {plans.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">
                    No procurement plans found
                  </div>
                ) : (
                  <div className="space-y-1">
                    {plans.map((plan) => (
                      <Button
                        key={plan._id}
                        variant="ghost"
                        onClick={() => handleSelectPlan(plan)}
                        className="w-full justify-start p-3 h-auto"
                      >
                        <div className="flex items-center gap-3 w-full">
                          <FileText className="w-4 h-4 flex-shrink-0 text-primary" />
                          <div className="flex-1 text-left">
                            <div className="font-medium">{plan.title}</div>
                            {plan.description && (
                              <div className="text-sm text-muted-foreground line-clamp-2">
                                {plan.description}
                              </div>
                            )}
                            <div className="flex items-center gap-2 mt-1">
                              {plan.budget && (
                                <span className="text-xs text-muted-foreground">
                                  {formatCurrency(plan.budget)}
                                </span>
                              )}
                              {plan.status && (
                                <Badge variant="secondary" className="text-xs">
                                  {plan.status}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                      </Button>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <div className="mt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onSelect("none")}
              className="text-xs"
            >
              No Procurement Plan
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProcurementPlanSelector;