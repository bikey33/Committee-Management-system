
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Upload, File } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface FileUploadProps {
  onFileChange: (file: File | null) => void;
  existingFile?: {
    name: string;
    size: number;
    onDownload: () => void;
  };
  disabled?: boolean;
}

const FileUpload = ({ onFileChange }: FileUploadProps) => {
  const { toast } = useToast();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const allowedTypes = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      ];

      if (!allowedTypes.includes(file.type)) {
        toast({
          title: "Invalid file type",
          description: "Please upload a PDF or Word document",
          variant: "destructive",
        });
        return;
      }

      if (file.size > 5 * 1024 * 1024) {
        toast({
          title: "File too large",
          description: "Maximum file size is 5MB",
          variant: "destructive",
        });
        return;
      }

      onFileChange(file);
      toast({
        title: "File selected",
        description: `File "${file.name}" ready for upload`,
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <File className="h-5 w-5 text-muted-foreground" />
        <Label htmlFor="committee-letter">Committee Formation Letter</Label>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
        <Input
          id="committee-letter"
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.doc,.docx"
          className="cursor-pointer file:mr-4 file:rounded-md file:border-0 file:px-4 file:py-2 file:text-sm file:font-medium file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
        />
        <Button type="button" variant="outline" className="flex w-full items-center justify-center gap-2 sm:w-auto">
          <Upload className="h-4 w-4" />
          Upload
        </Button>
      </div>
      <p className="text-sm text-muted-foreground">
        Accepted formats: PDF, DOC, DOCX (Max size: 5MB)
      </p>
    </div>
  );
};

export default FileUpload;
