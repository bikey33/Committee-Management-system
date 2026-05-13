
import { useState } from "react";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import type { SpecificationReview as SpecificationReviewType, DocumentStatus, CommitteeMember } from "@/types/committee";
import ReviewScheduler from "./review/ReviewScheduler";
import ReviewDocuments from "./review/ReviewDocuments";
import ReviewInfo from "./review/ReviewInfo";

interface SpecificationReviewProps {
  review: SpecificationReviewType;
  onScheduleReview: (date: string) => void;
  onAddMinutes: (minutes: string) => void;
  onUploadDocument: (file: File) => void;
  onUpdateStatus: (status: DocumentStatus) => void;
  onNotifyTeam?: (members: CommitteeMember[]) => void;
}

const SpecificationReview = ({
  review,
  onScheduleReview,
  onAddMinutes,
  onUploadDocument,
  onUpdateStatus,
  onNotifyTeam,
}: SpecificationReviewProps) => {
  const { toast } = useToast();
  const [minutes, setMinutes] = useState("");

  const handleMinutesSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAddMinutes(minutes);
    setMinutes("");
    toast({
      title: "Minutes Added",
      description: "Review minutes have been added successfully",
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUploadDocument(e.target.files[0]);
      toast({
        title: "Document Uploaded",
        description: "Review document has been uploaded successfully",
      });
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <Label>Schedule Review</Label>
          <ReviewScheduler
            onSchedule={onScheduleReview}
            onNotifyTeam={onNotifyTeam}
            reviewers={review.reviewers}
            scheduledDate={review.scheduledDate}
          />
        </div>

        <div className="space-y-4">
          <ReviewDocuments
            minutes={minutes}
            onMinutesChange={setMinutes}
            onMinutesSubmit={handleMinutesSubmit}
            onFileChange={handleFileChange}
          />
        </div>
      </div>

      <div>
        <Label htmlFor="status">Review Status</Label>
        <select
          id="status"
          value={review.status}
          onChange={(e) => onUpdateStatus(e.target.value as DocumentStatus)}
          className="w-full p-2 border rounded-md mt-2"
        >
          <option value="draft">Draft</option>
          <option value="submitted">Submitted</option>
          <option value="under_review">Under Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <ReviewInfo
        minutes={review.minutes}
        actualDate={review.actualDate}
        scheduledDate={review.scheduledDate}
        documents={review.documents}
        status={review.status}
      />
    </div>
  );
};

export default SpecificationReview;
