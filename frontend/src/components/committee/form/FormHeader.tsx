
import { Button } from "@/components/ui/button";
import { X, FileText } from "lucide-react";

interface FormHeaderProps {
  onClose: () => void;
}

const FormHeader = ({ onClose }: FormHeaderProps) => {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-xl">
            <FileText className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Committee Details</h2>
            <p className="text-gray-600 mt-1">Configure your committee structure and members</p>
          </div>
        </div>
        <Button
          onClick={onClose}
          variant="ghost"
          size="icon"
          className="rounded-full hover:bg-gray-100 transition-colors"
        >
          <X className="h-5 w-5 text-gray-500" />
        </Button>
      </div>
      
      {/* Progress Indicator */}
      <div className="flex items-center gap-2 mb-6">
        <div className="flex-1 h-2 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full"></div>
        <div className="flex-1 h-2 bg-gray-200 rounded-full"></div>
        <div className="flex-1 h-2 bg-gray-200 rounded-full"></div>
      </div>
    </div>
  );
};

export default FormHeader;
