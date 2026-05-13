import type { CommitteeMember } from "@/types/committee";
import { api } from "@/services/api";

export interface SubmissionData {
  name: string;
  purpose: string;
  committeeType: string;
  selectedProcurementPlan: string | null;
  formDate: string;
  specificationDate: string;
  reviewDate: string;
  members: CommitteeMember[];
  selectedFile: File | null;
}

export const createFormData = (data: SubmissionData): FormData => {
  const formData = new FormData();

  formData.append("name", data.name);
  formData.append("purpose", data.purpose);
  formData.append("committee_type", data.committeeType);

  if (data.selectedProcurementPlan && data.selectedProcurementPlan !== "none") {
    formData.append("procurement_plan", data.selectedProcurementPlan);
  }

  if (data.formDate) formData.append("formation_date", data.formDate);
  if (data.specificationDate) formData.append("specification_submission_date", data.specificationDate);
  if (data.reviewDate) formData.append("review_date", data.reviewDate);

  formData.append("should_notify", "true");

  const membersData = data.members.map((m) => ({
    employeeId: m.employeeId,
    role: m.role || "member",
  }));
  formData.append("members", JSON.stringify(membersData));

  if (data.selectedFile) {
    formData.append("formation_letter", data.selectedFile);
  }

  return formData;
};



export const submitCommitteeForm = async (formData: FormData): Promise<any> => {
  const response = await api.post("/api/committee/committees/create/", formData);
  return response.data;
};
