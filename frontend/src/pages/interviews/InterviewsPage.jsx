// src/pages/interviews/InterviewsPage.jsx
import { useNavigate } from "react-router-dom";
import { useInterviews, useDeleteInterview } from "../../hooks/useInterviews";
import { Button }   from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Mic, Briefcase, Trash2, ArrowRight,
  Plus, Code2, Users, Layers,
} from "lucide-react";
import { cn }     from "@/lib/utils";
import { format } from "date-fns";
import { toast }  from "sonner";

const TYPE_CONFIG = {
  behavioral: { label: "Behavioral", icon: Users,    color: "bg-blue-50   text-blue-700   border-blue-200"    },
  technical:  { label: "Technical",  icon: Code2,    color: "bg-violet-50 text-violet-700 border-violet-200"  },
  hr:         { label: "HR",         icon: Briefcase,color: "bg-emerald-50 text-emerald-700 border-emerald-200"},
  mixed:      { label: "Mixed",      icon: Layers,   color: "bg-amber-50  text-amber-700  border-amber-200"   },
};

function TypeBadge({ type }) {
  const cfg  = TYPE_CONFIG[type] ?? { label: type, color: "bg-slate-50 text-slate-500 border-slate-200" };
  const Icon = cfg.icon ?? Mic;
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border capitalize",
      cfg.color
    )}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function InterviewCard({ interview, onDelete }) {
  const navigate = useNavigate();
  return (
    <div
      onClick={() => navigate(`/interviews/${interview.id}`)}
      className="group flex items-center gap-4 px-5 py-4 border-b border-slate-100
                 hover:bg-slate-50/80 cursor-pointer transition-colors last:border-0"
    >
      {/* Icon */}
      <div className="w-9 h-9 rounded-xl bg-slate-100 flex items-center justify-center shrink-0
                      group-hover:bg-indigo-50 transition-colors">
        <Mic className="w-4 h-4 text-slate-500 group-hover:text-indigo-500 transition-colors" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm font-medium text-slate-900 truncate">{interview.title}</p>
          <TypeBadge type={interview.type} />
        </div>
        {interview.notes && (
          <p className="text-xs text-slate-400 truncate mt-0.5">{interview.notes}</p>
        )}
        <p className="text-xs text-slate-400 mt-0.5">
          {format(new Date(interview.created_at), "MMM d, yyyy")}
        </p>
      </div>

      {/* Actions */}
      <div
        className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={(e) => e.stopPropagation()}
      >
        <Button
          variant="ghost" size="icon"
          className="h-7 w-7 text-slate-400 hover:text-red-500 hover:bg-red-50"
          onClick={() => onDelete(interview.id)}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
        <ArrowRight className="w-4 h-4 text-slate-300 ml-1" />
      </div>
    </div>
  );
}

export default function InterviewsPage() {
  const navigate = useNavigate();
  const { data: interviews = [], isLoading, isError } = useInterviews();
  const deleteInterview = useDeleteInterview();

  const handleDelete = async (id) => {
    try {
      await deleteInterview.mutateAsync(id);
      toast.success("Interview deleted");
    } catch {
      toast.error("Failed to delete interview");
    }
  };

  // Count by type for summary pills
  const counts = interviews.reduce((acc, iv) => {
    acc[iv.type] = (acc[iv.type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-5 max-w-4xl mx-auto">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">Interviews</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {isLoading ? "Loading…" : `${interviews.length} interview${interviews.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => navigate("/interviews/new")}
          className="bg-slate-900 hover:bg-slate-700 text-white gap-1.5 h-8 px-3 text-xs font-medium"
        >
          <Plus className="w-3.5 h-3.5" />
          New Interview
        </Button>
      </div>

      {/* Type summary pills */}
      {!isLoading && interviews.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {Object.entries(TYPE_CONFIG).map(([type, cfg]) => {
            const count = counts[type] || 0;
            if (!count) return null;
            const Icon = cfg.icon;
            return (
              <div key={type} className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-medium",
                cfg.color
              )}>
                <Icon className="w-3.5 h-3.5" />
                {cfg.label} · {count}
              </div>
            );
          })}
        </div>
      )}

      {/* List */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {isError ? (
          <div className="py-14 text-center">
            <p className="text-sm text-slate-500">Failed to load interviews.</p>
          </div>
        ) : isLoading ? (
          <div className="p-5 space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="w-9 h-9 rounded-xl shrink-0" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-48 rounded" />
                  <Skeleton className="h-3 w-28 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : !interviews.length ? (
          <div className="py-16 text-center">
            <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
              <Mic className="w-6 h-6 text-slate-400" />
            </div>
            <p className="text-sm font-medium text-slate-700">No interviews yet</p>
            <p className="text-xs text-slate-400 mt-1 mb-4">
              Open a job and click "Create Interview"
            </p>
          </div>
        ) : (
          interviews.map((iv) => (
            <InterviewCard key={iv.id} interview={iv} onDelete={handleDelete} />
          ))
        )}
      </div>
    </div>
  );
}