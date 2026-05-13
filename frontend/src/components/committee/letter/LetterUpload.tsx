
import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Upload } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import type { CommitteeFormationLetter } from "@/types/letter";

interface LetterUploadProps {
  onUpload: (letter: CommitteeFormationLetter) => void;
}

const LetterUpload = ({ onUpload }: LetterUploadProps) => {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [purpose, setPurpose] = useState('');
  const { toast } = useToast();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.size > 5 * 1024 * 1024) {
        toast({
          title: "File too large",
          description: "Maximum file size is 5MB",
          variant: "destructive",
        });
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !referenceNumber || !purpose) {
      toast({
        title: "Missing information",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }

    const newLetter: CommitteeFormationLetter = {
      id: Date.now(),
      referenceNumber,
      issueDate: new Date().toISOString(),
      department: "Technical", // This would come from user context in real app
      purpose,
      fileUrl: URL.createObjectURL(file),
      fileName: file.name,
      version: 1,
      status: "draft",
      distributions: [],
      metadata: {
        createdBy: "Current User", // This would come from user context in real app
        createdAt: new Date().toISOString(),
        lastModified: new Date().toISOString(),
      },
    };

    onUpload(newLetter);
    setOpen(false);
    toast({
      title: "Letter uploaded",
      description: "Committee formation letter has been successfully uploaded",
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Upload className="h-4 w-4 mr-2" />
          Upload Letter
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Upload Committee Formation Letter</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="reference">Reference Number</Label>
            <Input
              id="reference"
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
              placeholder="NTC/2024/CF/XXX"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="purpose">Purpose</Label>
            <Input
              id="purpose"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="Committee formation purpose"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="file">Letter File</Label>
            <Input
              id="file"
              type="file"
              onChange={handleFileChange}
              accept=".pdf,.doc,.docx"
            />
          </div>
          <Button type="submit" className="w-full">
            Upload Letter
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default LetterUpload;
