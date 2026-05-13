
import { cn } from "@/lib/utils";
import type { CommitteeTask } from "@/types/committee";

interface TaskStatusSelectProps {
  status: CommitteeTask['status'];
  onStatusChange: (status: CommitteeTask['status']) => void;
}

const TaskStatusSelect = ({ status, onStatusChange }: TaskStatusSelectProps) => {
  const getStatusColor = (status: CommitteeTask['status']) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "in_progress":
        return "bg-blue-100 text-blue-800";
      case "overdue":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <select
      value={status}
      onChange={(e) => onStatusChange(e.target.value as CommitteeTask['status'])}
      className={cn(
        "px-3 py-1 rounded-full text-sm",
        getStatusColor(status)
      )}
    >
      <option value="pending">Pending</option>
      <option value="in_progress">In Progress</option>
      <option value="completed">Completed</option>
      <option value="overdue">Overdue</option>
    </select>
  );
};

export default TaskStatusSelect;
