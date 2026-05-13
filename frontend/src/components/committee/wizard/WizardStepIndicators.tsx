import { CheckCircle } from "lucide-react";
import { WIZARD_STEPS, type WizardStep } from "./WizardConfig";

interface WizardStepIndicatorsProps {
  currentStep: number;
  isStepValid: (step: number) => boolean;
}

const WizardStepIndicators = ({ currentStep, isStepValid }: WizardStepIndicatorsProps) => {
  return (
    <div className="flex justify-between items-center">
      {WIZARD_STEPS.map((step: WizardStep) => {
        const Icon = step.icon;
        const isCompleted = currentStep > step.id;
        const isCurrent = currentStep === step.id;

        return (
          <div
            key={step.id}
            className={`flex flex-col items-center space-y-2 flex-1 ${
              isCurrent ? "text-primary" : isCompleted ? "text-primary" : "text-muted-foreground"
            }`}
          >
            <div
            className={`w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all duration-300 hover-scale ${
              isCurrent
                ? "border-primary bg-primary text-primary-foreground shadow-lg"
                : isCompleted
                ? "border-primary bg-primary text-primary-foreground"
                : "border-muted bg-background"
            }`}
            >
              {isCompleted ? (
                <CheckCircle className="w-6 h-6" />
              ) : (
                <Icon className="w-6 h-6" />
              )}
            </div>
            <div className="text-center">
              <p className={`font-medium text-sm ${isCurrent ? "text-primary" : ""}`}>
                {step.title}
              </p>
              <p className="text-xs text-muted-foreground hidden sm:block">
                {step.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default WizardStepIndicators;