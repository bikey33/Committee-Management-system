
import { ListCheck } from "lucide-react";

const TaskFormHeader = () => {
  return (
    <div className="flex items-center gap-2 mb-4">
      <ListCheck className="h-5 w-5 text-muted-foreground" />
      <h3 className="text-lg font-semibold">Create New Task</h3>
    </div>
  );
};

export default TaskFormHeader;
