import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { CalendarIcon, Upload, FileText, AlertCircle } from "lucide-react";
import { format, addDays } from "date-fns";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface DocumentsStepProps {
  formDate: string;
  specificationDate: string;
  reviewDate: string;
  selectedFile: File | null;
  deadlineDays: number;
  onFormDateChange: (value: string) => void;
  onSpecificationDateChange: (value: string) => void;
  onReviewDateChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
  onDeadlineDaysChange: (days: number) => void;
}

const formatLocalDate = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
};

const parseLocalDate = (value: string): Date => {
  const [year, month, day] = value.split("-").map((part) => parseInt(part, 10));
  return new Date(year, (month || 1) - 1, day || 1);
};

const DocumentsStep = ({
  formDate,
  specificationDate,
  reviewDate,
  selectedFile,
  deadlineDays,
  onFormDateChange,
  onSpecificationDateChange,
  onReviewDateChange,
  onFileChange,
  onDeadlineDaysChange,
}: DocumentsStepProps) => {

  const [dragActive, setDragActive] = useState(false);

  const handleFileUpload = (file: File) => {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];

    if (file.size > maxSize) {
      toast.error("File Too Large", {
        description: "Please select a file smaller than 10MB",
      });
      return;
    }

    if (!allowedTypes.includes(file.type)) {
      toast.error("Invalid File Type", {
        description: "Please select a PDF or Word document",
      });
      return;
    }

    onFileChange(file);
    toast.success("File Uploaded", {
      description: `${file.name} has been uploaded successfully`,
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const calculateDeadline = () => {
    if (formDate) {
      return addDays(parseLocalDate(formDate), deadlineDays);
    }
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Formation Date */}
      <div className="space-y-2">
        <Label>
          Formation Date <span className="text-destructive">*</span>
        </Label>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                "w-full justify-start text-left font-normal",
                !formDate && "text-muted-foreground"
              )}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {formDate ? format(parseLocalDate(formDate), "PPP") : "Select formation date"}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={formDate ? parseLocalDate(formDate) : undefined}
              onSelect={(date) => onFormDateChange(date ? formatLocalDate(date) : "")}
              initialFocus
              className="pointer-events-auto"
            />
          </PopoverContent>
        </Popover>
      </div>

      {/* Deadline Configuration */}
      <div className="space-y-2">
        <Label htmlFor="deadline-days">Deadline (Days from Formation)</Label>
        <div className="flex items-center space-x-4">
          <Input
            id="deadline-days"
            type="number"
            min="1"
            max="365"
            value={deadlineDays}
            onChange={(e) => onDeadlineDaysChange(parseInt(e.target.value) || 30)}
            className="w-24"
          />
          <span className="text-sm text-muted-foreground">
            days {calculateDeadline() && `(${format(calculateDeadline()!, "PPP")})`}
          </span>
        </div>
      </div>

      {/* Optional Dates */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-2">
          <Label>Specification Submission Date (Optional)</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !specificationDate && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {specificationDate ? format(parseLocalDate(specificationDate), "PPP") : "Select date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={specificationDate ? parseLocalDate(specificationDate) : undefined}
                onSelect={(date) => onSpecificationDateChange(date ? formatLocalDate(date) : "")}
                initialFocus
                className="pointer-events-auto"
              />
            </PopoverContent>
          </Popover>
        </div>

        <div className="space-y-2">
          <Label>Review Date (Optional)</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !reviewDate && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {reviewDate ? format(parseLocalDate(reviewDate), "PPP") : "Select date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={reviewDate ? parseLocalDate(reviewDate) : undefined}
                onSelect={(date) => onReviewDateChange(date ? formatLocalDate(date) : "")}
                initialFocus
                className="pointer-events-auto"
              />
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* File Upload */}
      <div className="space-y-2">
        <Label>Formation Letter (Optional)</Label>
        <div
          className={cn(
            "relative border-2 border-dashed rounded-lg p-6 text-center transition-colors",
            dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25",
            selectedFile ? "bg-green-50 border-green-300" : "hover:border-muted-foreground/50"
          )}
          onDrop={handleDrop}
          onDragOver={handleDrag}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
        >
          {selectedFile ? (
            <div className="space-y-2">
              <FileText className="h-8 w-8 text-green-600 mx-auto" />
              <p className="text-sm font-medium text-green-800">{selectedFile.name}</p>
              <p className="text-xs text-green-600">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onFileChange(null)}
              >
                Remove File
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <Upload className="h-8 w-8 text-muted-foreground mx-auto" />
              <div>
                <p className="text-sm font-medium">Drop your formation letter here</p>
                <p className="text-xs text-muted-foreground">or click to browse</p>
              </div>
              <input
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
            </div>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Supported formats: PDF, DOC, DOCX (Max 10MB)
        </p>
      </div>

      {/* Date Validation Warning */}
      {formDate && specificationDate && new Date(specificationDate) < new Date(formDate) && (
        <div className="flex items-start gap-2 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="text-sm">
            <p className="font-medium text-amber-800">Date Validation Warning:</p>
            <p className="text-amber-700">
              Specification submission date should not be earlier than the formation date.
            </p>
          </div>
        </div>
      )}

      <div className="bg-muted/50 p-4 rounded-lg">
        <h4 className="font-medium text-sm mb-2">Document Guidelines</h4>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>• Formation date is required and marks the official start of the committee</li>
          <li>• Deadline is automatically calculated from the formation date</li>
          <li>• Specification and review dates are optional but help track milestones</li>
          <li>• Formation letter attachment is optional but recommended for official records</li>
          <li>• All dates should be logically sequenced</li>
        </ul>
      </div>
    </div>
  );
};

export default DocumentsStep;
