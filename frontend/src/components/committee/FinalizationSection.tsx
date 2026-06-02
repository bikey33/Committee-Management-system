import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload, FileText } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";

interface FinalizationSectionProps {
  committeeId: string;
  isInitializationComplete: boolean;
  onReportSubmit?: (data: { notes: string; file?: File }) => Promise<void>;
}

export function FinalizationSection({
  committeeId,
  isInitializationComplete,
  onReportSubmit,
}: FinalizationSectionProps) {
  const [reportNotes, setReportNotes] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isMarked, setIsMarked] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const { toast } = useToast();

  if (!isInitializationComplete) {
    return null;
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      toast({
        title: "File uploaded",
        description: `${file.name} ready to submit`,
      });
    }
  };

  const handleSaveNotes = async () => {
    if (!reportNotes.trim()) {
      toast({
        title: "Note required",
        description: "Please enter report notes before saving",
        variant: "destructive",
      });
      return;
    }

    try {
      setIsSaving(true);
      if (onReportSubmit) {
        await onReportSubmit({ notes: reportNotes, file: uploadedFile || undefined });
      }
      toast({
        title: "Success",
        description: "Report notes saved successfully",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to save notes",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleMarkComplete = () => {
    setIsMarked(true);
    toast({
      title: "Finalization marked complete",
      description: "Committee has completed all finalization tasks",
    });
  };

  return (
    <Card className="border-0 shadow-sm rounded-lg overflow-hidden">
      <CardHeader className="bg-gradient-to-r from-blue-600 to-blue-700 text-white px-6 py-4 flex flex-row items-center justify-between">
        <div>
          <CardTitle className="text-base font-semibold">Phase 2</CardTitle>
          <p className="text-sm text-blue-100 mt-1">Finalization</p>
        </div>
        <Button
          onClick={handleMarkComplete}
          disabled={isMarked}
          className="bg-white text-blue-600 hover:bg-blue-50"
          size="sm"
        >
          <span className="relative w-4 h-4 mr-2 flex items-center justify-center">
            ⊙
          </span>
          {isMarked ? "Marked Complete" : "Mark Finalization Complete"}
        </Button>
      </CardHeader>

      <CardContent className="p-6 space-y-6">
        {/* Reporting Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-gray-600" />
            <h3 className="font-semibold text-gray-900">Reporting</h3>
          </div>

          {/* File Upload */}
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Final Report (PDF / Doc)</p>
                {uploadedFile && (
                  <p className="text-xs text-green-600 mt-1">
                    ✓ {uploadedFile.name}
                  </p>
                )}
              </div>
              <label>
                <input
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <Button
                  variant="default"
                  size="sm"
                  className="cursor-pointer"
                  onClick={(e) => {
                    const input = (e.target as HTMLElement).parentElement?.querySelector('input');
                    input?.click();
                  }}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Upload report
                </Button>
              </label>
            </div>
          </div>

          {/* Notes Section */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-900">
              Report Notes / Summary
            </label>
            <textarea
              value={reportNotes}
              onChange={(e) => setReportNotes(e.target.value)}
              placeholder="Outcome, recommendations, key findings..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={6}
            />
          </div>

          {/* Save Button */}
          <Button
            onClick={handleSaveNotes}
            disabled={isSaving}
            variant="outline"
            className="bg-gray-100 text-gray-900 hover:bg-gray-200 border-gray-300"
          >
            {isSaving ? "Saving..." : "Save Notes"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default FinalizationSection;
