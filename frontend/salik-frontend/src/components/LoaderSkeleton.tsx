export default function LoaderSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-8 w-3/4 rounded-full bg-white/10" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 space-y-4 shadow-[0_12px_30px_rgba(2,6,23,0.18)]"
          >
            <div className="h-4 w-1/2 rounded-full bg-white/10" />
            <div className="h-4 w-3/4 rounded-full bg-white/10" />
            <div className="h-4 w-1/3 rounded-full bg-white/10" />
            <div className="h-20 rounded-xl bg-white/10" />
          </div>
        ))}
      </div>
    </div>
  );
}

