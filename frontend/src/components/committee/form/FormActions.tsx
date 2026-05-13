// form/FormActions.tsx
import { Button } from "@/components/ui/button";
import { Bell, Loader2 } from "lucide-react"; // Add Loader2 for loading spinner

interface FormActionsProps {
  onClose: () => void;
  isLoading?: boolean;
  isEditMode?: boolean;
}

const FormActions = ({ onClose, isLoading = false, isEditMode = false }: FormActionsProps) => {
  return (
    <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 sm:gap-4 mt-8 pt-6 border-t">
      <Button 
        type="button" 
        variant="outline" 
        onClick={onClose}
        className="w-full sm:w-auto"
        disabled={isLoading}
      >
        Cancel
      </Button>
      <Button 
        type="submit" 
        className="w-full sm:w-auto bg-gradient-to-r from-indigo-500 to-blue-500 hover:from-indigo-600 hover:to-blue-600 text-white flex items-center justify-center gap-2"
        disabled={isLoading}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <>
            <Bell className="h-4 w-4" />
            {isEditMode ? "Update & Notify" : "Create & Notify"}
          </>
        )}
      </Button>
    </div>
  );
};

export default FormActions;