import { Briefcase, Building2, Trash2, Pencil, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import LevelBadge from "./LevelBadge";

export default function JobCard({ job, onView, onEdit, onDelete }) {
  return (
    <tr
      onClick={() => onView(job)}
      className="group cursor-pointer border-b border-slate-100 hover:bg-slate-50/80 transition-colors"
    >
      {/* Position */}
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 group-hover:bg-indigo-50 transition-colors">
            <Briefcase className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-500 transition-colors" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-900">{job.title}</p>
            <div className="flex items-center gap-1 mt-0.5 text-xs text-slate-400">
              <Building2 className="w-3 h-3" />
              {job.company}
            </div>
          </div>
        </div>
      </td>

      {/* Level */}
      <td className="px-4 py-3.5">
        <LevelBadge level={job.seniority_level} />
      </td>

      {/* Date */}
      <td className="px-4 py-3.5 text-sm text-slate-500 hidden md:table-cell">
        {job.created_at ? format(new Date(job.created_at), "MMM d, yyyy") : "—"}
      </td>

      {/* Actions */}
      <td
        className="px-4 py-3.5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            onClick={(e) => { e.stopPropagation(); onEdit(job); }}
          >
            <Pencil className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-slate-400 hover:text-red-500 hover:bg-red-50"
            onClick={(e) => { e.stopPropagation(); onDelete(job); }}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
          <ChevronRight className="w-4 h-4 text-slate-300 ml-1" />
        </div>
      </td>
    </tr>
  );
}

export function JobCardSkeleton() {
  return Array.from({ length: 4 }).map((_, i) => (
    <tr key={i} className="border-b border-slate-100">
      <td className="px-4 py-3.5">
        <div className="flex items-center gap-3">
          <Skeleton className="w-8 h-8 rounded-lg shrink-0" />
          <div className="space-y-1.5">
            <Skeleton className="h-3.5 w-32 rounded" />
            <Skeleton className="h-3 w-20 rounded" />
          </div>
        </div>
      </td>
      <td className="px-4 py-3.5"><Skeleton className="h-5 w-16 rounded-full" /></td>
      <td className="px-4 py-3.5 hidden md:table-cell"><Skeleton className="h-3.5 w-24 rounded" /></td>
      <td className="px-4 py-3.5" />
    </tr>
  ));
}