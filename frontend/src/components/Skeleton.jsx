// Loading skeletons. Cheap on purpose: CSS pulse only, no layout thrash.
export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded bg-slate-800 ${className}`} aria-hidden="true" />;
}

/** Skeleton matching the score panel while a scan runs. */
export function ResultSkeleton() {
  return (
    <section className="grid gap-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-6 md:grid-cols-[240px_1fr]">
      <Skeleton className="mx-auto h-48 w-52 rounded-xl" />
      <div className="flex flex-col gap-3">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-9 w-40" />
      </div>
    </section>
  );
}

/** Skeleton for the reason cards. */
export function ReasonsSkeleton({ cards = 3 }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: cards }, (_, i) => (
        <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 flex flex-col gap-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
        </div>
      ))}
    </div>
  );
}

/** Skeleton for community report cards. */
export function ReportsSkeleton({ cards = 3 }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: cards }, (_, i) => (
        <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 flex flex-col gap-2">
          <div className="flex gap-2">
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-24 rounded-full" />
          </div>
          <Skeleton className="h-3 w-2/3" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}
