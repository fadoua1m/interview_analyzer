import { useJobs } from "../hooks/useJobs";
import { Briefcase, TrendingUp, Clock, Star, ArrowRight, Plus } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { cn } from "@/lib/utils";
import { format } from "date-fns";

// ── Level badge inline ───────────────────────────────────────────────────────
const LEVEL_COLORS = {
  junior: "text-sky-600    bg-sky-50    border-sky-200",
  mid:    "text-violet-600 bg-violet-50 border-violet-200",
  senior: "text-amber-600  bg-amber-50  border-amber-200",
  lead:   "text-rose-600   bg-rose-50   border-rose-200",
};

function LevelPill({ level }) {
  return (
    <span className={cn(
      "text-[11px] font-medium px-2 py-0.5 rounded-full border capitalize",
      LEVEL_COLORS[level] ?? "text-slate-500 bg-slate-50 border-slate-200"
    )}>
      {level}
    </span>
  );
}

// ── Stat card ────────────────────────────────────────────────────────────────
function StatCard({ icon: Icon, label, value, sub, color, loading, comingSoon }) {
  return (
    <div className={cn(
      "bg-white rounded-2xl border border-slate-200 p-5 flex flex-col gap-3 shadow-sm",
      "hover:shadow-md transition-shadow duration-200 relative overflow-hidden"
    )}>
      {/* Background accent */}
      <div className={cn("absolute top-0 right-0 w-20 h-20 rounded-full opacity-5 -translate-y-6 translate-x-6", color)} />

      <div className="flex items-start justify-between">
        <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center", color)}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        {comingSoon && (
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full border border-slate-200">
            Soon
          </span>
        )}
      </div>

      <div>
        {loading ? (
          <Skeleton className="h-8 w-16 rounded-lg mb-1" />
        ) : (
          <p className="text-3xl font-bold text-slate-900 tabular-nums leading-none">
            {comingSoon ? "—" : value}
          </p>
        )}
        <p className="text-sm font-medium text-slate-600 mt-1">{label}</p>
        {sub && !comingSoon && (
          <p className="text-xs text-slate-400 mt-0.5">{sub}</p>
        )}
        {comingSoon && (
          <p className="text-xs text-slate-400 mt-0.5">Coming soon</p>
        )}
      </div>
    </div>
  );
}

// ── Recent job row ───────────────────────────────────────────────────────────
function RecentJobRow({ job }) {
  return (
    <div className="flex items-center gap-3 py-3 border-b border-slate-100 last:border-0 group">
      <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 group-hover:bg-indigo-50 transition-colors">
        <Briefcase className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-500 transition-colors" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate">{job.title}</p>
        <p className="text-xs text-slate-400 truncate">{job.company}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <LevelPill level={job.seniority_level} />
        {job.created_at && (
          <span className="text-xs text-slate-400 hidden sm:block">
            {format(new Date(job.created_at), "MMM d")}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Level distribution bar ───────────────────────────────────────────────────
function LevelBar({ jobs }) {
  const counts = { junior: 0, mid: 0, senior: 0, lead: 0 };
  jobs.forEach((j) => { if (counts[j.seniority_level] !== undefined) counts[j.seniority_level]++; });
  const total = jobs.length || 1;

  const bars = [
    { key: "junior", label: "Junior", color: "bg-sky-400" },
    { key: "mid",    label: "Mid",    color: "bg-violet-400" },
    { key: "senior", label: "Senior", color: "bg-amber-400" },
    { key: "lead",   label: "Lead",   color: "bg-rose-400" },
  ];

  return (
    <div className="space-y-3">
      {bars.map(({ key, label, color }) => (
        <div key={key} className="flex items-center gap-3">
          <span className="text-xs text-slate-500 w-12 shrink-0">{label}</span>
          <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all duration-700", color)}
              style={{ width: `${(counts[key] / total) * 100}%` }}
            />
          </div>
          <span className="text-xs font-medium text-slate-600 w-5 text-right shrink-0">
            {counts[key]}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { data: jobs = [], isLoading } = useJobs();
  const navigate = useNavigate();

  const recentJobs  = [...jobs].slice(0, 5);
  const seniorCount = jobs.filter((j) => j.seniority_level === "senior" || j.seniority_level === "lead").length;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => navigate("/jobs")}
          className="bg-slate-900 hover:bg-slate-700 text-white gap-1.5 text-xs h-8 px-3"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Job
        </Button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Briefcase}
          label="Total Jobs"
          value={jobs.length}
          sub={`${recentJobs.length} added recently`}
          color="bg-indigo-500"
          loading={isLoading}
        />
        <StatCard
          icon={Star}
          label="Senior / Lead"
          value={seniorCount}
          sub="senior & lead roles"
          color="bg-amber-500"
          loading={isLoading}
        />
        <StatCard
          icon={TrendingUp}
          label="Match Rate"
          value="—"
          color="bg-emerald-500"
          loading={false}
          comingSoon
        />
        <StatCard
          icon={Clock}
          label="Interviews"
          value="—"
          color="bg-rose-500"
          loading={false}
          comingSoon
        />
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">

        {/* Recent jobs — 3 cols */}
        <div className="lg:col-span-3 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Recent Jobs</h2>
              <p className="text-xs text-slate-400 mt-0.5">Latest positions added</p>
            </div>
            <button
              onClick={() => navigate("/jobs")}
              className="flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700 font-medium transition-colors"
            >
              View all
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="px-5">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 py-3 border-b border-slate-100 last:border-0">
                  <Skeleton className="w-8 h-8 rounded-lg" />
                  <div className="flex-1 space-y-1.5">
                    <Skeleton className="h-3.5 w-36 rounded" />
                    <Skeleton className="h-3 w-24 rounded" />
                  </div>
                </div>
              ))
            ) : !recentJobs.length ? (
              <div className="py-10 text-center">
                <Briefcase className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500">No jobs yet</p>
                <button
                  onClick={() => navigate("/jobs")}
                  className="text-xs text-indigo-500 hover:underline mt-1"
                >
                  Add your first job →
                </button>
              </div>
            ) : (
              recentJobs.map((job) => <RecentJobRow key={job.id} job={job} />)
            )}
          </div>
        </div>

        {/* Level breakdown — 2 cols */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100">
            <h2 className="text-sm font-semibold text-slate-900">By Seniority</h2>
            <p className="text-xs text-slate-400 mt-0.5">Distribution across levels</p>
          </div>
          <div className="px-5 py-5">
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-3 w-12 rounded" />
                    <Skeleton className="h-2 flex-1 rounded-full" />
                    <Skeleton className="h-3 w-4 rounded" />
                  </div>
                ))}
              </div>
            ) : !jobs.length ? (
              <div className="py-8 text-center">
                <p className="text-sm text-slate-400">No data yet</p>
              </div>
            ) : (
              <LevelBar jobs={jobs} />
            )}
          </div>

          {/* Coming soon placeholder */}
          <div className="mx-5 mb-5 rounded-xl bg-slate-50 border border-dashed border-slate-200 px-4 py-4 text-center">
            <p className="text-xs font-medium text-slate-400">More analytics coming soon</p>
            <p className="text-[11px] text-slate-300 mt-0.5">Match scores · Interview tracking</p>
          </div>
        </div>

      </div>
    </div>
  );
}