
import { Badge } from "@/components/ui/badge";
import { Clock, FileText } from "lucide-react";
import { format } from "date-fns";
import type { DocumentStatus } from "@/types/committee";

interface ReviewInfoProps {
  minutes?: string;
  actualDate?: string;
  scheduledDate: string;
  documents: File[];
  status: DocumentStatus;
}

const ReviewInfo = ({
  minutes,
  actualDate,
  scheduledDate,
  documents,
  status,
}: ReviewInfoProps) => {
  const getStatusBadgeColor = (status: DocumentStatus) => {
    switch (status) {
      case "approved":
        return "bg-green-100 text-green-800";
      case "rejected":
        return "bg-red-100 text-red-800";
      case "under_review":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="space-y-4">
      <Badge className={getStatusBadgeColor(status)}>
        {status.replace("_", " ").toUpperCase()}
      </Badge>

      {minutes && (
        <div className="p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-gray-500" />
            <h4 className="font-medium">Previous Minutes</h4>
          </div>
          <p className="text-sm text-gray-600">{minutes}</p>
          <div className="flex items-center gap-2 mt-2 text-sm text-gray-500">
            <Clock className="h-4 w-4" />
            <span>Last updated: {format(new Date(actualDate || scheduledDate), "PPP")}</span>
          </div>
        </div>
      )}

      {documents.length > 0 && (
        <div className="p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium mb-2">Uploaded Documents</h4>
          <div className="space-y-2">
            {documents.map((doc, index) => (
              <div key={index} className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4 text-gray-500" />
                <span>{doc.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ReviewInfo;
