import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { FileText, Zap } from "lucide-react";
import CommitteeFormationWizard from "./CommitteeFormationWizard";
import type { Committee } from "@/types/committee";
import type { ProcurementPlan } from "@/types/procurement-plan";

interface CommitteeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateCommittee?: (committee: Committee) => void;
  preSelectedPlan?: ProcurementPlan;
}

const CommitteeDialog = ({ open, onOpenChange, onCreateCommittee, preSelectedPlan }: CommitteeDialogProps) => {
  const [mode, setMode] = useState<"select" | "wizard" | "quick">("select");

  const handleClose = () => {
    setMode("select");
    onOpenChange(false);
  };

  const renderContent = () => {
    switch (mode) {
      case "wizard":
        return (
          <CommitteeFormationWizard
            onClose={handleClose}
            onCreateCommittee={onCreateCommittee}
            preSelectedPlan={preSelectedPlan}
          />
        );
      case "quick":
        return (
          <div className="text-center py-8">
            <p className="text-muted-foreground">Quick form coming soon...</p>
            <Button variant="outline" onClick={() => setMode("select")} className="mt-4">
              Back to Options
            </Button>
          </div>
        );
      default:
        return (
          <div className="space-y-6">
            <div className="text-center">
              <h2 className="text-2xl font-bold mb-2">Create New Committee</h2>
              <p className="text-muted-foreground">Choose how you'd like to create your committee</p>
            </div>

            <div className="grid gap-4">
              <div
                onClick={() => setMode("wizard")}
                className="p-6 border rounded-lg cursor-pointer hover:border-primary transition-all duration-300 hover-scale hover:shadow-md"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                    <FileText className="w-6 h-6 text-primary" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold">Step-by-Step Wizard</h3>
                    <p className="text-sm text-muted-foreground">
                      Guided process with validation, member search, and document upload
                    </p>
                  </div>
                </div>
              </div>

              <div
                onClick={() => setMode("quick")}
                className="p-6 border rounded-lg cursor-pointer hover:border-primary transition-all duration-300 hover-scale opacity-50 hover:opacity-75"
              >
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                    <Zap className="w-6 h-6 text-primary" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold">Quick Form</h3>
                    <p className="text-sm text-muted-foreground">Simple form for experienced users (Coming Soon)</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        {mode === "select" && (
          <DialogHeader>
            <DialogTitle>Committee Creation</DialogTitle>
          </DialogHeader>
        )}
        {renderContent()}
      </DialogContent>
    </Dialog>
  );
};

export default CommitteeDialog;
