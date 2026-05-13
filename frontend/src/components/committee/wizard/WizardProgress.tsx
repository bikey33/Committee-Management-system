import { Progress } from "@/components/ui/progress";
import { WIZARD_STEPS } from "./WizardConfig";

interface WizardProgressProps {
  currentStep: number;
}

const WizardProgress = ({ currentStep }: WizardProgressProps) => {
  const progressPercentage = (currentStep / WIZARD_STEPS.length) * 100;

  return (
    <div className="space-y-4">
      <Progress value={progressPercentage} className="h-2" />
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>Step {currentStep} of {WIZARD_STEPS.length}</span>
        <span>{Math.round(progressPercentage)}% Complete</span>
      </div>
    </div>
  );
};

export default WizardProgress;