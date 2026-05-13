
import { Clock } from "lucide-react";
import { format } from "date-fns";
import type { CommitteeMember, CommitteeTask } from "@/types/committee";
import TaskStatusSelect from "./TaskStatusSelect";

interface TaskListItemProps {
  task: CommitteeTask;
  assignedMember?: CommitteeMember;
  onStatusChange: (status: CommitteeTask['status']) => void;
}

const TaskListItem = ({ task, assignedMember, onStatusChange }: TaskListItemProps) => {
  return (
    <div className="p-4 border rounded-lg bg-white shadow-sm">
      <div className="flex justify-between items-start gap-4">
        <div className="space-y-1">
          <h4 className="font-medium">{task.title}</h4>
          <p className="text-sm text-gray-500">{task.description}</p>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Clock className="h-4 w-4" />
            Due: {format(new Date(task.dueDate), "PPP")}
          </div>
          {assignedMember && (
            <p className="text-sm text-gray-500">
              Assigned to: {assignedMember.name}
            </p>
          )}
        </div>
        <TaskStatusSelect 
          status={task.status} 
          onStatusChange={(status) => onStatusChange(status)} 
        />
      </div>
    </div>
  );
};

export default TaskListItem;

