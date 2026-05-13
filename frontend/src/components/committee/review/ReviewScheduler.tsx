
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar as CalendarIcon, Users } from "lucide-react";
import { format } from "date-fns";
import type { CommitteeMember } from "@/types/committee";

interface ReviewSchedulerProps {
  onSchedule: (date: string) => void;
  onNotifyTeam?: (members: CommitteeMember[]) => void;
  reviewers: CommitteeMember[];
  scheduledDate?: string;
}

const ReviewScheduler = ({ 
  onSchedule, 
  onNotifyTeam,
  reviewers,
  scheduledDate 
}: ReviewSchedulerProps) => {
  const [date, setDate] = useState<Date>();

  const handleSchedule = () => {
    if (!date) return;
    onSchedule(date.toISOString());
    
    if (onNotifyTeam && reviewers.length > 0) {
      onNotifyTeam(reviewers);
    }
    setDate(undefined);
  };

  return (
    <div className="space-y-4">
      <div>
        <div className="flex gap-4 mt-2">
          <Popover>
            <PopoverTrigger asChild>
              <Button variant="outline" className="w-full justify-start text-left font-normal">
                <CalendarIcon className="mr-2 h-4 w-4" />
                {date ? format(date, "PPP") : <span>Pick a date</span>}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0">
              <Calendar
                mode="single"
                selected={date}
                onSelect={setDate}
                initialFocus
              />
            </PopoverContent>
          </Popover>
          <Button onClick={handleSchedule}>Schedule</Button>
        </div>
      </div>

      <div className="mt-2 p-4 border rounded-lg">
        <div className="flex items-center gap-2 mb-3">
          <Users className="h-4 w-4 text-gray-500" />
          <span className="text-sm text-gray-500">
            {reviewers.length} team members
          </span>
        </div>
        <div className="space-y-2">
          {reviewers.map((member) => (
            <div key={member.id} className="text-sm">
              {member.name} ({member.role})
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ReviewScheduler;
