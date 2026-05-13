import { FileText, Users, Calendar, Settings } from "lucide-react";

export interface WizardStep {
  id: number;
  title: string;
  description: string;
  icon: typeof FileText;
}

export const WIZARD_STEPS: WizardStep[] = [
  {
    id: 1,
    title: "Basic Information",
    description: "Committee Name, Purpose & Type",
    icon: FileText,
  },
  {
    id: 2,
    title: "Committee Members",
    description: "Add Members & Assign Roles",
    icon: Users,
  },
  {
    id: 3,
    title: "Documents & Dates",
    description: "Upload Formation Letter & Set Dates",
    icon: Calendar,
  },
  {
    id: 4,
    title: "Review & Submit",
    description: "Review & Finalize Committee",
    icon: Settings,
  },
];