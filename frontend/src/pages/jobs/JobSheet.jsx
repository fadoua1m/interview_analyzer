import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Briefcase, Building2, Pencil, Calendar, RefreshCw } from "lucide-react";
import { format } from "date-fns";
import LevelBadge from "./LevelBadge";

export default function JobSheet({ job, open, onClose, onEdit }) {
  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent
        side="right"
        className="w-full sm:w-[520px] lg:w-[600px] overflow-y-auto p-0"
      >
        {/* Sticky header */}
        <SheetHeader className="px-6 py-5 border-b border-slate-100 bg-white sticky top-0 z-10">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center shrink-0">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <SheetTitle className="text-base font-semibold text-slate-900 leading-tight">
                {job?.title}
              </SheetTitle>
              <SheetDescription className="text-sm text-slate-500 mt-0.5 flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 shrink-0" />
                {job?.company}
              </SheetDescription>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <LevelBadge level={job?.seniority_level} />
              <Button
                variant="outline"
                size="sm"
                className="h-7 px-2.5 text-xs gap-1.5"
                onClick={() => { onClose(); onEdit(job); }}
              >
                <Pencil className="w-3 h-3" />
                Edit
              </Button>
            </div>
          </div>
        </SheetHeader>

        {/* Body */}
        <div className="px-6 py-6 space-y-6">

          {/* Timestamps */}
          <div className="flex gap-4 flex-wrap">
            {job?.created_at && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Calendar className="w-3.5 h-3.5" />
                Added {format(new Date(job.created_at), "MMMM d, yyyy")}
              </div>
            )}
            {job?.updated_at && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <RefreshCw className="w-3.5 h-3.5" />
                Updated {format(new Date(job.updated_at), "MMM d, yyyy")}
              </div>
            )}
          </div>

          {/* Description */}
          {job?.description && (
            <section className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Job Description
              </h3>
              <div className="bg-slate-50 rounded-xl px-4 py-3 border border-slate-100">
                <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
                  {job.description}
                </p>
              </div>
            </section>
          )}

          {/* Requirements */}
          {job?.requirements && (
            <section className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Requirements
              </h3>
              <div className="bg-slate-50 rounded-xl px-4 py-3 border border-slate-100">
                <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
                  {job.requirements}
                </p>
              </div>
            </section>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}