import type { CounterfactualJob } from "../types/api";

interface LoadingStatusProps {
  job: CounterfactualJob | null;
}

export function LoadingStatus({ job }: LoadingStatusProps) {
  if (!job || job.status === "completed") {
    return null;
  }

  return (
    <div className="status-strip" role="status">
      <strong>{job.status}</strong>
      <span>Phase: {job.phase}</span>
      <span>Search calls: {job.progress.search_calls}</span>
      {job.message ? <span>{job.message}</span> : null}
    </div>
  );
}
