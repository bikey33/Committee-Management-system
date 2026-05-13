import { Button } from "@/components/ui/button";
import { ArrowLeft, ArrowRight, CheckCircle } from "lucide-react";
import { WIZARD_STEPS } from "./WizardConfig";

interface WizardNavigationProps {
  currentStep: number;
  isStepValid: (step: number) => boolean;
  isSubmitting: boolean;
  onPrevStep: () => void;
  onNextStep: () => void;
  onSubmit: () => void;
  onClose: () => void;
}

const WizardNavigation = ({
  currentStep,
  isStepValid,
  isSubmitting,
  onPrevStep,
  onNextStep,
  onSubmit,
  onClose,
}: WizardNavigationProps) => {
  return (
    <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-100 shadow-sm mt-8">
      <Button
        onClick={onPrevStep}
        disabled={currentStep === 1}
        className="flex items-center gap-2 bg-[hsl(209,100%,32%)] hover:bg-[hsl(209,100%,25%)] text-white px-6 font-semibold shadow-md transition-all active:scale-95 disabled:opacity-50 disabled:bg-slate-300"
      >
        <ArrowLeft className="w-4 h-4" />
        Previous
      </Button>

      <div className="flex gap-3">
        <Button
          variant="ghost"
          onClick={onClose}
          className="text-slate-500 hover:text-slate-700 font-medium"
        >
          Cancel
        </Button>

        {currentStep < WIZARD_STEPS.length ? (
          <Button
            onClick={onNextStep}
            className="flex items-center gap-2 bg-[hsl(209,100%,32%)] hover:bg-[hsl(209,100%,25%)] text-white px-8 font-semibold shadow-md transition-all active:scale-95"
          >
            Next
            <ArrowRight className="w-4 h-4" />
          </Button>
        ) : (
          <Button
            onClick={onSubmit}
            disabled={!isStepValid(currentStep) || isSubmitting}
            className="flex items-center gap-2 bg-[hsl(209,100%,32%)] hover:bg-[hsl(209,100%,25%)] text-white px-8 font-semibold shadow-md transition-all active:scale-95"
          >
            {isSubmitting ? "Creating..." : "Create Committee"}
            <CheckCircle className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  );
};

export default WizardNavigation;