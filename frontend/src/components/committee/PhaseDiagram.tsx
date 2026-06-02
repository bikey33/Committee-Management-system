import React from "react";
import { Check, Lock, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface Phase {
  phase: string;
  name: string;
  order: number;
  completed: boolean;
  visible: boolean;
  completion_percentage: number;
  checkpoints: Array<{
    id: number;
    name: string;
    is_completed: boolean;
    phase: string;
  }>;
}

interface PhaseDiagramProps {
  phases: Phase[];
  initializationComplete?: boolean;
}

export function PhaseDiagram({ phases, initializationComplete = false }: PhaseDiagramProps) {
  const visiblePhases = phases.filter(p => p.visible !== false);

  if (!visiblePhases.length) {
    return null;
  }

  return (
    <div className="w-full space-y-8">
      {/* Phase Flow Diagram */}
      <div className="flex items-center justify-between gap-2 sm:gap-4">
        {visiblePhases.map((phase, index) => (
          <React.Fragment key={phase.phase}>
            {/* Phase Box */}
            <div className="flex flex-col items-center flex-1 min-w-0">
              <div
                className={cn(
                  "relative w-full flex flex-col items-center px-3 py-4 rounded-lg border-2 transition-all",
                  phase.completed
                    ? "bg-green-50 border-green-400 shadow-sm"
                    : phase.visible === false
                      ? "bg-gray-50 border-gray-300"
                      : "bg-blue-50 border-blue-400 shadow-sm",
                )}
              >
                {/* Phase Icon */}
                <div
                  className={cn(
                    "rounded-full p-2.5 mb-2",
                    phase.completed
                      ? "bg-green-200"
                      : phase.visible === false
                        ? "bg-gray-200"
                        : "bg-blue-200",
                  )}
                >
                  {phase.completed ? (
                    <Check className="w-5 h-5 text-green-700" />
                  ) : phase.visible === false ? (
                    <Lock className="w-5 h-5 text-gray-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-blue-700" />
                  )}
                </div>

                {/* Phase Name and Status */}
                <h3 className="font-semibold text-sm text-center text-foreground mb-1">
                  {phase.name}
                </h3>

                {/* Completion Percentage */}
                <div className="text-xs text-muted-foreground mb-2">
                  {phase.completed ? (
                    <span className="text-green-700 font-medium">100% Complete</span>
                  ) : (
                    <span>{phase.completion_percentage}% Complete</span>
                  )}
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      phase.completed ? "bg-green-500" : "bg-blue-500",
                    )}
                    style={{ width: `${phase.completion_percentage}%` }}
                  />
                </div>
              </div>

              {/* Checkpoint Count */}
              <div className="text-xs text-muted-foreground mt-2 text-center">
                {phase.checkpoints.filter(cp => cp.is_completed).length}/{phase.checkpoints.length}{" "}
                checkpoints
              </div>
            </div>

            {/* Arrow Connector (not on last phase) */}
            {index < visiblePhases.length - 1 && (
              <div className="flex-shrink-0 mb-10">
                <div className="flex items-center gap-1 text-gray-400">
                  <div className="w-6 h-0.5 bg-gray-300" />
                  <span className="text-xs">→</span>
                </div>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Phase Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {visiblePhases.map((phase) => (
          <div
            key={phase.phase}
            className={cn(
              "p-4 rounded-lg border",
              phase.completed
                ? "bg-green-50 border-green-200"
                : phase.visible === false
                  ? "bg-gray-50 border-gray-200"
                  : "bg-blue-50 border-blue-200",
            )}
          >
            <h4 className="font-semibold text-sm mb-3">{phase.name} Checkpoints</h4>
            <ul className="space-y-2">
              {phase.checkpoints.map((checkpoint) => (
                <li key={checkpoint.id} className="flex items-start gap-2 text-sm">
                  <div className="flex-shrink-0 mt-0.5">
                    {checkpoint.is_completed ? (
                      <Check className="w-4 h-4 text-green-600" />
                    ) : (
                      <div className="w-4 h-4 rounded border border-gray-300" />
                    )}
                  </div>
                  <span
                    className={cn(
                      "text-sm",
                      checkpoint.is_completed ? "text-green-700 line-through" : "text-foreground",
                    )}
                  >
                    {checkpoint.name}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Locked Phase Message */}
      {!initializationComplete && phases.some(p => p.phase === "finalization") && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
          <div className="flex items-start gap-3">
            <Lock className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div>
              <h4 className="font-semibold text-sm text-amber-900">Finalization Phase Locked</h4>
              <p className="text-xs text-amber-700 mt-1">
                Complete all checkpoints in the Initialization phase to unlock the Finalization phase and access reporting options.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PhaseDiagram;
