import React, { useState } from "react";
import { Check, CheckCircle2, Circle, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

interface Checkpoint {
  id: number;
  name: string;
  description?: string;
  is_completed: boolean;
  completed_date?: string;
  completedBy?: {
    id: string;
    name: string;
    email: string;
  };
  notes?: string;
  order: number;
  phase: string;
}

interface CheckpointsProgressProps {
  checkpoints: Checkpoint[];
  phase: string;
  phaseName: string;
  isLocked?: boolean;
  onCompleteCheckpoint?: (checkpointId: number) => Promise<void>;
  isEditable?: boolean;
}

export function CheckpointsProgress({
  checkpoints,
  phase,
  phaseName,
  isLocked = false,
  onCompleteCheckpoint,
  isEditable = false,
}: CheckpointsProgressProps) {
  const [expandedCheckpoint, setExpandedCheckpoint] = useState<number | null>(null);
  const [completingId, setCompletingId] = useState<number | null>(null);

  const completedCount = checkpoints.filter(cp => cp.is_completed).length;
  const completionPercentage = checkpoints.length > 0 ? Math.round((completedCount / checkpoints.length) * 100) : 0;

  const handleCompleteCheckpoint = async (checkpointId: number) => {
    if (!onCompleteCheckpoint) return;

    try {
      setCompletingId(checkpointId);
      await onCompleteCheckpoint(checkpointId);
    } catch (error) {
      console.error("Failed to complete checkpoint:", error);
    } finally {
      setCompletingId(null);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return null;
    try {
      return format(new Date(dateString), "MMM d, yyyy");
    } catch {
      return null;
    }
  };

  return (
    <Card className={cn("overflow-hidden", isLocked && "opacity-60 pointer-events-none")}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg">{phaseName} Phase</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {completedCount} of {checkpoints.length} checkpoints completed
            </p>
          </div>
          <Badge variant={completionPercentage === 100 ? "default" : "outline"} className="flex-shrink-0">
            {completionPercentage}%
          </Badge>
        </div>

        {/* Progress Bar */}
        <div className="mt-3 space-y-1">
          <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                completionPercentage === 100 ? "bg-green-500" : "bg-blue-500",
              )}
              style={{ width: `${completionPercentage}%` }}
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {checkpoints.length === 0 ? (
          <div className="py-6 text-center">
            <p className="text-sm text-muted-foreground">No checkpoints available for this phase.</p>
          </div>
        ) : (
          checkpoints.map((checkpoint) => (
            <div key={checkpoint.id} className="space-y-2">
              {/* Checkpoint Item */}
              <button
                onClick={() =>
                  setExpandedCheckpoint(expandedCheckpoint === checkpoint.id ? null : checkpoint.id)
                }
                className="w-full flex items-start gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors text-left"
              >
                {/* Status Icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {checkpoint.is_completed ? (
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                  ) : (
                    <Circle className="w-5 h-5 text-gray-300" />
                  )}
                </div>

                {/* Checkpoint Info */}
                <div className="flex-1 min-w-0">
                  <p
                    className={cn(
                      "font-medium text-sm",
                      checkpoint.is_completed ? "text-green-700 line-through" : "text-foreground",
                    )}
                  >
                    {checkpoint.name}
                  </p>
                  {checkpoint.description && (
                    <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                      {checkpoint.description}
                    </p>
                  )}
                </div>

                {/* Expand Indicator */}
                <div className="flex-shrink-0">
                  {expandedCheckpoint === checkpoint.id ? (
                    <ChevronUp className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-muted-foreground" />
                  )}
                </div>
              </button>

              {/* Expanded Details */}
              {expandedCheckpoint === checkpoint.id && (
                <div className="ml-8 space-y-3 pt-2 pb-3 border-t">
                  {checkpoint.description && (
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                        Description
                      </p>
                      <p className="text-sm text-foreground mt-1">{checkpoint.description}</p>
                    </div>
                  )}

                  {checkpoint.is_completed && checkpoint.completed_date && (
                    <div className="flex items-start gap-2 text-sm">
                      <Calendar className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                      <div>
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                          Completed
                        </p>
                        <p className="text-sm text-foreground mt-0.5">
                          {formatDate(checkpoint.completed_date)}
                        </p>
                      </div>
                    </div>
                  )}

                  {checkpoint.is_completed && checkpoint.completedBy && (
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                        Completed By
                      </p>
                      <p className="text-sm text-foreground mt-1">{checkpoint.completedBy.name}</p>
                      <p className="text-xs text-muted-foreground">{checkpoint.completedBy.email}</p>
                    </div>
                  )}

                  {checkpoint.notes && (
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                        Notes
                      </p>
                      <p className="text-sm text-foreground mt-1">{checkpoint.notes}</p>
                    </div>
                  )}

                  {!checkpoint.is_completed && isEditable && onCompleteCheckpoint && (
                    <Button
                      onClick={() => handleCompleteCheckpoint(checkpoint.id)}
                      disabled={completingId === checkpoint.id}
                      size="sm"
                      className="mt-3 w-full"
                    >
                      {completingId === checkpoint.id ? (
                        <>
                          <span className="animate-spin mr-2">⏳</span>
                          Marking complete...
                        </>
                      ) : (
                        <>
                          <Check className="w-4 h-4 mr-2" />
                          Mark as Complete
                        </>
                      )}
                    </Button>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}

// Chevron Icons (from lucide-react or create inline)
function ChevronUp(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" {...props}>
      <polyline points="18 15 12 9 6 15"></polyline>
    </svg>
  );
}

function ChevronDown(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" {...props}>
      <polyline points="6 9 12 15 18 9"></polyline>
    </svg>
  );
}

export default CheckpointsProgress;
