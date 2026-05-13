
import { CheckSquare } from "lucide-react";
import { isAfter, isBefore } from "date-fns";
import type { CommitteeMember, CommitteeTask } from "@/types/committee";
import TaskListItem from "./fields/TaskListItem";

interface TaskListProps {
  members: CommitteeMember[];
  tasks: CommitteeTask[];
  onTaskUpdate: (taskId: number, status: CommitteeTask['status']) => void;
}

const TaskList = ({ members, tasks, onTaskUpdate }: TaskListProps) => {
  const checkTaskStatus = (task: CommitteeTask) => {
    const now = new Date();
    const dueDate = new Date(task.dueDate);
    
    if (task.status !== "completed" && isBefore(dueDate, now)) {
      onTaskUpdate(task.id, "overdue");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <CheckSquare className="h-5 w-5 text-muted-foreground" />
        <h3 className="text-lg font-semibold">Current Tasks</h3>
      </div>
      <div className="space-y-2">
        {tasks.map((task) => {
          checkTaskStatus(task);
          const assignedMember = members.find(m => m.id === task.assignedTo);
          return (
            <TaskListItem
              key={task.id}
              task={task}
              assignedMember={assignedMember}
              onStatusChange={(status) => onTaskUpdate(task.id, status)}
            />
          );
        })}

        {tasks.length === 0 && (
          <div className="text-center py-8 text-muted-foreground border rounded-lg">
            No tasks created yet. Use the form above to create your first task.
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskList;

