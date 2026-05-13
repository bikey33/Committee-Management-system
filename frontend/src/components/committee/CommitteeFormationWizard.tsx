import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText } from "lucide-react";
import { useCommitteeForm } from "@/hooks/useCommitteeForm";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import type { Committee } from "@/types/committee";
import type { ProcurementPlan } from "@/types/procurement-plan";
import { useQueryClient } from "@tanstack/react-query";

// Step Components
import BasicInfoStep from "./wizard/BasicInfoStep";
import MembersStep from "./wizard/MembersStep";
import DocumentsStep from "./wizard/DocumentsStep";
import ReviewStep from "./wizard/ReviewStep";

// Wizard Components
import WizardProgress from "./wizard/WizardProgress";
import WizardStepIndicators from "./wizard/WizardStepIndicators";
import WizardNavigation from "./wizard/WizardNavigation";
import { WIZARD_STEPS } from "./wizard/WizardConfig";
import { validateStep, validateAllSteps } from "./wizard/WizardValidation";
import { createFormData, submitCommitteeForm, type SubmissionData } from "./wizard/WizardSubmission";

interface CommitteeFormationWizardProps {
  onClose: () => void;
  onCreateCommittee?: (committee: Committee) => void;
  preSelectedPlan?: ProcurementPlan;
  defaultCommitteeType?: string;
}

const CommitteeFormationWizard = ({ onClose, onCreateCommittee, preSelectedPlan, defaultCommitteeType }: CommitteeFormationWizardProps) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { token } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const {
    name,
    purpose,
    formDate,
    selectedFile,
    members,
    setName,
    setPurpose,
    setFormDate,
    setSelectedFile,
    setMembers,
    handleAddMember,
    handleAddMemberWithData,
    handleUpdateMember,
    resetForm,
  } = useCommitteeForm(onClose, onCreateCommittee);

  // Wizard state
  const [committeeType, setCommitteeType] = useState<string>(defaultCommitteeType || "");
  const [selectedProcurementPlan, setSelectedProcurementPlan] = useState<string | null>(
    preSelectedPlan ? preSelectedPlan.id.toString() : null
  );
  const [selectedPlanName, setSelectedPlanName] = useState<string>("");
  const [specificationDate, setSpecificationDate] = useState("");
  const [reviewDate, setReviewDate] = useState("");
  const [deadlineDays, setDeadlineDays] = useState(30);

  const isStepValid = (step: number): boolean => {
    return validateStep(step, { name, purpose, committeeType, selectedProcurementPlan, members, formDate });
  };

  const nextStep = () => {
    if (currentStep < WIZARD_STEPS.length && isStepValid(currentStep)) {
      setCurrentStep(currentStep + 1);
      return;
    }

    if (!isStepValid(currentStep)) {
      if (currentStep === 2) {
        const hasCoordinator = members.some((m) => {
          const r = (m.role || "").toLowerCase();
          return r === "chairperson" || r === "coordinator" || r === "co-ordinator";
        });
        if (!hasCoordinator) {
          toast.warning("Missing Co-ordinator", {
            description: "Please assign exactly one Co-ordinator for this committee.",
          });
          return;
        }
      }

      toast.error("Incomplete Information", {
        description: "Please complete all required fields before proceeding.",
      });
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    if (!validateAllSteps({ name, purpose, committeeType, selectedProcurementPlan, members, formDate })) {
      toast.error("Validation Error", {
        description: "Please complete all required information in all steps.",
      });
      return;
    }

    try {
      setIsSubmitting(true);

      if (!token) {
        throw new Error("No authentication token found. Please log in.");
      }

      const submissionData: SubmissionData = {
        name,
        purpose,
        committeeType,
        selectedProcurementPlan,
        formDate,
        specificationDate,
        reviewDate,
        members,
        selectedFile,
      };

      const formData = createFormData(submissionData);
      const data = await submitCommitteeForm(formData);

      toast.success("Committee Created Successfully", {
        description: "The committee has been created and members have been notified.",
      });

      queryClient.invalidateQueries({ queryKey: ["committees"] });
      if (selectedProcurementPlan) {
        queryClient.invalidateQueries({ queryKey: ["committee", "plan", selectedProcurementPlan] });
      }

      if (onCreateCommittee) {
        onCreateCommittee(data.committee || data);
      }

      resetForm();
      onClose();
    } catch (error) {
      console.error("Error creating committee:", error);

      if (error instanceof Error && error.message === "UNAUTHORIZED") {
        toast.error("Session Expired", {
          description: "Your session has expired. Please log in again.",
        });
        navigate("/login");
        return;
      }

      if (error instanceof Error && !error.message.includes("Please log in again")) {
        toast.error("Error", {
          description: error.message || "Failed to create committee",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveMember = (index: number) => {
    setMembers(members.filter((_, i) => i !== index));
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <BasicInfoStep
            name={name}
            purpose={purpose}
            committeeType={committeeType}
            selectedProcurementPlan={selectedProcurementPlan}
            onNameChange={setName}
            onPurposeChange={setPurpose}
            onCommitteeTypeChange={setCommitteeType}
            onProcurementPlanChange={setSelectedProcurementPlan}
            onPlanNameChange={setSelectedPlanName}
            preSelectedPlan={preSelectedPlan}
          />
        );
      case 2:
        return (
          <MembersStep
            members={members}
            onAddMember={handleAddMemberWithData}
            onUpdateMember={handleUpdateMember}
            onRemoveMember={handleRemoveMember}
          />
        );
      case 3:
        return (
          <DocumentsStep
            formDate={formDate}
            specificationDate={specificationDate}
            reviewDate={reviewDate}
            selectedFile={selectedFile}
            deadlineDays={deadlineDays}
            onFormDateChange={setFormDate}
            onSpecificationDateChange={setSpecificationDate}
            onReviewDateChange={setReviewDate}
            onFileChange={setSelectedFile}
            onDeadlineDaysChange={setDeadlineDays}
          />
        );
      case 4:
        return (
          <ReviewStep
            name={name}
            purpose={purpose}
            committeeType={committeeType}
            selectedProcurementPlan={selectedProcurementPlan}
            selectedPlanName={selectedPlanName}
            formDate={formDate}
            specificationDate={specificationDate}
            reviewDate={reviewDate}
            members={members}
            selectedFile={selectedFile}
            deadlineDays={deadlineDays}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="w-full p-2 md:p-4 lg:p-6 space-y-6 animate-fade-in">
      <div className="text-center space-y-1">
        <h1 className="text-xl font-bold text-[hsl(209,100%,32%)] tracking-tight">Committee Formation Wizard</h1>
        <p className="text-sm font-semibold text-slate-500 leading-relaxed">Create a new committee in 4 simple steps</p>
      </div>

      {/* Progress Bar */}
      <WizardProgress currentStep={currentStep} />

      {/* Step Indicators */}
      <WizardStepIndicators currentStep={currentStep} isStepValid={isStepValid} />

      {/* Step Content */}
      <Card className="border-t-4 border-t-[hsl(209,100%,32%)] shadow-sm overflow-hidden">
        <CardHeader className="pb-3 border-b border-slate-50">
          <CardTitle className="flex items-center gap-2 text-lg font-bold text-[hsl(209,100%,32%)] tracking-tight">
            {(() => {
              const Icon = WIZARD_STEPS[currentStep - 1]?.icon || FileText;
              return <Icon className="w-5 h-5" />;
            })()}
            {WIZARD_STEPS[currentStep - 1]?.title}
          </CardTitle>
          <p className="text-xs font-bold text-slate-400 mt-1 ml-7">
            {currentStep === 2
              ? `Add members and assign their roles (${members.length} Member${members.length !== 1 ? 's' : ''} Added)`
              : WIZARD_STEPS[currentStep - 1]?.description}
          </p>
        </CardHeader>
        <CardContent className="p-6 space-y-6">{renderStepContent()}</CardContent>
      </Card>

      {/* Navigation */}
      <WizardNavigation
        currentStep={currentStep}
        isStepValid={isStepValid}
        isSubmitting={isSubmitting}
        onPrevStep={prevStep}
        onNextStep={nextStep}
        onSubmit={handleSubmit}
        onClose={onClose}
      />
    </div>
  );
};

export default CommitteeFormationWizard;
