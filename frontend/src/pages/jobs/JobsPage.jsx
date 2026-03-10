import { useState } from "react";
import { useJobs } from "../../hooks/useJobs";
import { Button } from "@/components/ui/button";
import { Briefcase, Plus, X, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import JobCard, { JobCardSkeleton } from "./JobCard";
import JobFormDialog from "./JobFormDialog";
import DeleteDialog from "./DeleteDialog";
import JobSheet from "./JobSheet";

export default function JobsPage() {
  const { data: jobs = [], isLoading, isError } = useJobs();

  const [viewJob,    setViewJob]    = useState(null);
  const [editJob,    setEditJob]    = useState(null);
  const [deleteJob,  setDeleteJob]  = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [search,     setSearch]     = useState("");
  const [levelFilter, setLevelFilter] = useState("all");

  const LEVELS = ["all", "junior", "mid", "senior", "lead"];

  const filtered = jobs.filter((job) => {
    const matchSearch =
      job.title.toLowerCase().includes(search.toLowerCase()) ||
      job.company.toLowerCase().includes(search.toLowerCase());
    const matchLevel =
      levelFilter === "all" || job.seniority_level === levelFilter;
    return matchSearch && matchLevel;
  });

  return (
    <div className="space-y-5 max-w-6xl mx-auto">

      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Jobs</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {isLoading
              ? "Loading…"
              : `${filtered.length} of ${jobs.length} positions`}
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setShowCreate(true)}
          className="bg-slate-900 hover:bg-slate-700 text-white gap-1.5 h-8 px-3 text-xs font-medium shrink-0"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Job
        </Button>
      </div>

      {/* Filters bar */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <Input
            placeholder="Search title or company…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-8 text-sm bg-white"
          />
        </div>

        {/* Level pills */}
        <div className="flex gap-1.5 flex-wrap">
          {LEVELS.map((lvl) => (
            <button
              key={lvl}
              onClick={() => setLevelFilter(lvl)}
              className={cn(
                "px-3 py-1 rounded-lg text-xs font-medium border capitalize transition-all",
                levelFilter === lvl
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-slate-500 border-slate-200 hover:bg-slate-50 hover:text-slate-700"
              )}
            >
              {lvl === "all" ? "All levels" : lvl}
            </button>
          ))}
        </div>
      </div>

      {/* Table card */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        {isError ? (
          <div className="px-4 py-16 text-center">
            <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-3">
              <X className="w-5 h-5 text-red-400" />
            </div>
            <p className="text-sm font-medium text-slate-700">Failed to load jobs</p>
            <p className="text-xs text-slate-400 mt-1">Check your connection and try again</p>
          </div>
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80">
                {["Position", "Level", "Added", ""].map((h, i) => (
                  <th
                    key={i}
                    className={cn(
                      "px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider",
                      i === 2 && "hidden md:table-cell"
                    )}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <JobCardSkeleton />
              ) : !filtered.length ? (
                <tr>
                  <td colSpan={4} className="px-4 py-16 text-center">
                    <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                      <Briefcase className="w-5 h-5 text-slate-400" />
                    </div>
                    {jobs.length === 0 ? (
                      <>
                        <p className="text-sm font-medium text-slate-700">No jobs yet</p>
                        <p className="text-xs text-slate-400 mt-1 mb-4">
                          Add your first position to get started
                        </p>
                        <Button
                          size="sm"
                          onClick={() => setShowCreate(true)}
                          className="bg-slate-900 hover:bg-slate-700 text-white gap-1.5 text-xs"
                        >
                          <Plus className="w-3.5 h-3.5" />
                          Add Job
                        </Button>
                      </>
                    ) : (
                      <>
                        <p className="text-sm font-medium text-slate-700">No results found</p>
                        <p className="text-xs text-slate-400 mt-1">
                          Try adjusting your search or filter
                        </p>
                        <button
                          onClick={() => { setSearch(""); setLevelFilter("all"); }}
                          className="text-xs text-indigo-500 hover:underline mt-2"
                        >
                          Clear filters
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ) : (
                filtered.map((job) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    onView={setViewJob}
                    onEdit={setEditJob}
                    onDelete={setDeleteJob}
                  />
                ))
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Modals & panels */}
      <JobFormDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
      />
      <JobFormDialog
        open={!!editJob}
        onClose={() => setEditJob(null)}
        initial={editJob}
      />
      <DeleteDialog
        job={deleteJob}
        open={!!deleteJob}
        onClose={() => setDeleteJob(null)}
      />
      <JobSheet
        job={viewJob}
        open={!!viewJob}
        onClose={() => setViewJob(null)}
        onEdit={(job) => { setViewJob(null); setEditJob(job); }}
      />
    </div>
  );
}