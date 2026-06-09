import React from "react";
import { cn } from "@/lib/utils";
import { Check, Lock } from "lucide-react";
import type { Committee, CommitteePhase } from "@/api/committees";

type StepState = "complete" | "current" | "upcoming";

interface Step {
  key: string;
  label: string;
  caption: string;
  state: StepState;
}

const PRIMARY = "hsl(209,100%,32%)";

function isClosedStatus(status?: string) {
  const s = (status || "").toLowerCase();
  return s === "completed" || s === "dissolved";
}

function StatusPill({ committee }: { committee: Committee }) {
  const finalDone = !!committee.finalization_phase_completed;
  const closed = isClosedStatus(committee.committee_status) || finalDone;
  const overdue =
    !closed &&
    !!committee.deadline &&
    new Date(committee.deadline).getTime() < Date.now();

  const label = closed ? "Closed" : overdue ? "Overdue" : "Active";
  const classes = closed
    ? "bg-slate-100 text-slate-600 border-slate-200"
    : overdue
    ? "bg-rose-50 text-rose-600 border-rose-200"
    : "bg-emerald-50 text-emerald-600 border-emerald-200";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold",
        classes
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          closed ? "bg-slate-400" : overdue ? "bg-rose-500" : "bg-emerald-500"
        )}
      />
      {label}
    </span>
  );
}

interface CommitteeStepperProps {
  committee: Committee;
}

export function CommitteeStepper({ committee }: CommitteeStepperProps) {
  const initDone = !!committee.initialization_phase_completed;
  const finalDone = !!committee.finalization_phase_completed;
  const closed = isClosedStatus(committee.committee_status) || finalDone;

  const steps: Step[] = [
    {
      key: "initialization",
      label: "Initialization",
      caption: initDone ? "Completed" : "In progress",
      state: initDone ? "complete" : "current",
    },
    {
      key: "in_progress",
      label: "In Progress",
      caption: !initDone ? "Locked" : finalDone ? "Completed" : "In progress",
      state: !initDone ? "upcoming" : finalDone ? "complete" : "current",
    },
    {
      key: "completed",
      label: "Completed",
      caption: closed ? "Closed" : "Pending",
      state: closed ? "complete" : finalDone ? "current" : "upcoming",
    },
  ];

  // The active phase whose checkpoint progress we surface in the bar.
  const phases: CommitteePhase[] = committee.phases || [];
  const activePhaseKey = !initDone ? "initialization" : !finalDone ? "finalization" : null;
  const activePhase = activePhaseKey
    ? phases.find((p) => p.phase === activePhaseKey)
    : null;

  const checkpoints = activePhase?.checkpoints || [];
  const completedCount = checkpoints.filter((c) => c.is_completed).length;
  const totalCount = checkpoints.length;
  const pct = activePhase
    ? activePhase.completion_percentage ?? (totalCount ? Math.round((completedCount / totalCount) * 100) : 0)
    : 100;

  const headingStep = steps.find((s) => s.state === "current") || steps[steps.length - 1];

  return (
    <div className="w-full rounded-lg border border-slate-200 bg-white p-6">
      <div className="mb-6 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
            Committee Progress
          </p>
          <h3 className="text-lg font-bold text-slate-900">
            {closed ? "Completed" : headingStep.label}
          </h3>
        </div>
        <StatusPill committee={committee} />
      </div>

      {/* Stepper */}
      <div className="flex items-start">
        {steps.map((step, index) => {
          const isComplete = step.state === "complete";
          const isCurrent = step.state === "current";
          const prevComplete = index > 0 && steps[index - 1].state === "complete";

          return (
            <React.Fragment key={step.key}>
              <div className="flex flex-1 flex-col items-center gap-2 text-center">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full border-2 text-sm font-bold transition-colors",
                    isComplete && "border-transparent text-white",
                    isCurrent && "bg-white",
                    step.state === "upcoming" && "border-slate-200 bg-slate-50 text-slate-300"
                  )}
                  style={
                    isComplete
                      ? { backgroundColor: PRIMARY }
                      : isCurrent
                      ? { borderColor: PRIMARY, color: PRIMARY }
                      : undefined
                  }
                >
                  {isComplete ? (
                    <Check className="h-5 w-5" />
                  ) : step.state === "upcoming" ? (
                    <Lock className="h-4 w-4" />
                  ) : (
                    index + 1
                  )}
                </div>
                <div>
                  <p
                    className={cn(
                      "text-sm font-bold",
                      step.state === "upcoming" ? "text-slate-400" : "text-slate-900"
                    )}
                  >
                    {step.label}
                  </p>
                  <p
                    className={cn(
                      "text-[11px] font-medium",
                      isCurrent ? "text-[hsl(209,100%,32%)]" : "text-slate-400"
                    )}
                  >
                    {step.caption}
                  </p>
                </div>
              </div>

              {index < steps.length - 1 && (
                <div className="mt-5 h-0.5 flex-1">
                  <div
                    className="h-full w-full rounded-full"
                    style={{ backgroundColor: prevComplete ? PRIMARY : "#e2e8f0" }}
                  />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Checkpoint progress for the active phase */}
      {activePhase && totalCount > 0 && (
        <div className="mt-6">
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-600">
              {activePhase.name} checkpoints
            </span>
            <span className="font-bold text-slate-700">
              {completedCount}/{totalCount} · {pct}%
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full transition-all"
              style={{ width: `${pct}%`, backgroundColor: PRIMARY }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default CommitteeStepper;
