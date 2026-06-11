import React from "react";
import { cn } from "@/lib/utils";
import { Check, Lock } from "lucide-react";
import type { Committee } from "@/api/committees";

type StepState = "complete" | "current" | "upcoming";

interface Step {
  key: string;
  label: string;
  caption: string;
  state: StepState;
}

const PRIMARY = "hsl(209,100%,32%)";

const IN_PROGRESS_STATUSES = ["active"];
const COMPLETED_STATUSES = ["completed", "dissolved"];

function isInProgressStage(committee: Committee) {
  return IN_PROGRESS_STATUSES.includes(committee.committee_status || "");
}

function isCompletedStage(committee: Committee) {
  return COMPLETED_STATUSES.includes(committee.committee_status || "");
}

function StatusPill({ committee }: { committee: Committee }) {
  const done = isCompletedStage(committee);
  const inProg = isInProgressStage(committee);
  const overdue =
    !done &&
    !!committee.deadline &&
    new Date(committee.deadline).getTime() < Date.now();

  const label = done ? "Completed" : overdue ? "Overdue" : inProg ? "In Progress" : "Initialization";
  const classes = done
    ? "bg-slate-100 text-slate-600 border-slate-200"
    : overdue
    ? "bg-rose-50 text-rose-600 border-rose-200"
    : inProg
    ? "bg-blue-50 text-blue-600 border-blue-200"
    : "bg-amber-50 text-amber-600 border-amber-200";

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
          done ? "bg-slate-400" : overdue ? "bg-rose-500" : inProg ? "bg-blue-500" : "bg-amber-500"
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
  const inProgress = isInProgressStage(committee);
  const done = isCompletedStage(committee);

  const steps: Step[] = [
    {
      key: "initialization",
      label: "Initialization",
      caption: inProgress || done ? "Completed" : "In progress",
      state: inProgress || done ? "complete" : "current",
    },
    {
      key: "in_progress",
      label: "In Progress",
      caption: done ? "Completed" : inProgress ? "In progress" : "Locked",
      state: done ? "complete" : inProgress ? "current" : "upcoming",
    },
    {
      key: "completed",
      label: "Completed",
      caption: done ? "Closed" : "Pending",
      state: done ? "complete" : "upcoming",
    },
  ];

  const headingStep = steps.find((s) => s.state === "current") || steps[steps.length - 1];

  return (
    <div className="w-full rounded-lg border border-slate-200 bg-white p-6">
      <div className="mb-6 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
            Committee Progress
          </p>
          <h3 className="text-lg font-bold text-slate-900">
            {done ? "Completed" : headingStep.label}
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
    </div>
  );
}

export default CommitteeStepper;
