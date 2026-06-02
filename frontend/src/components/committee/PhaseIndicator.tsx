import React from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, Circle } from "lucide-react";

interface Phase {
  phase: string;
  name: string;
  status: string;
  date?: string;
  visible: boolean;
}

interface PhaseIndicatorProps {
  phases: Phase[];
  initializationComplete?: boolean;
}

export function PhaseIndicator({ phases, initializationComplete = false }: PhaseIndicatorProps) {
  const visiblePhases = phases.filter(p => p.visible !== false);

  if (!visiblePhases.length) {
    return null;
  }

  return (
    <div className="w-full bg-white rounded-lg border border-gray-200 p-6 mb-6">
      <div className="flex items-center justify-between gap-8">
        {visiblePhases.map((phase, index) => (
          <React.Fragment key={phase.phase}>
            <div className="flex flex-col items-center gap-2">
              <div className="flex items-center justify-center">
                {phase.phase === "initialization" ? (
                  initializationComplete ? (
                    <CheckCircle2 className="w-12 h-12 text-blue-600" />
                  ) : (
                    <Circle className="w-12 h-12 text-gray-300 border-2 border-blue-600" />
                  )
                ) : initializationComplete ? (
                  <Circle className="w-12 h-12 text-gray-400 border-2 border-gray-400" />
                ) : (
                  <Circle className="w-12 h-12 text-gray-300 border-2 border-gray-300" />
                )}
              </div>
              <div className="text-center">
                <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">
                  Phase {index + 1}
                </p>
                <p className="text-sm font-bold text-gray-900">{phase.name}</p>
                <p className="text-xs text-gray-600 mt-1">
                  {phase.status}
                  {phase.date && ` ${phase.date}`}
                </p>
              </div>
            </div>

            {index < visiblePhases.length - 1 && (
              <div className="flex-1 h-0.5 bg-blue-600 mb-8 min-w-[40px]"></div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

export default PhaseIndicator;
