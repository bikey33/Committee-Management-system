import type { CommitteeMember } from "@/types/committee";

export const validateStep = (
  step: number,
  data: {
    name: string;
    purpose: string;
    committeeType: string;
    selectedProcurementPlan: string | null;
    members: CommitteeMember[];
    formDate: string;
  }
): boolean => {
  switch (step) {
    case 1:
      return (
        data.name.length >= 3 &&
        data.purpose.length >= 10 &&
        data.committeeType !== "" &&
        data.selectedProcurementPlan !== null
      );
    case 2:
      return (
        data.members.length > 0 &&
        data.members.some((m) => {
          const r = (m.role || "").toLowerCase();
          return r === "chairperson" || r === "coordinator" || r === "co-ordinator";
        }) &&
        data.members.every((m) => m.employeeId && m.name && m.email)
      );
    case 3:
      return data.formDate !== "";
    case 4:
      return true;
    default:
      return false;
  }
};

export const validateAllSteps = (data: {
  name: string;
  purpose: string;
  committeeType: string;
  selectedProcurementPlan: string | null;
  members: CommitteeMember[];
  formDate: string;
}): boolean => {
  return validateStep(1, data) && validateStep(2, data) && validateStep(3, data);
};
