import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Upload, FileVideo, CheckCircle2 } from "lucide-react";
import { useCandidateAccess, useSubmitCandidateVideo } from "../../hooks/useInterviews";

export default function CandidateSubmissionPage() {
  const { token } = useParams();
  const { data, isLoading, isError } = useCandidateAccess(token);
  const submitVideo = useSubmitCandidateVideo(token);

  const [file, setFile] = useState(null);
  const [analysis, setAnalysis] = useState(null);

  const canSubmit = useMemo(() => {
    if (!data) return false;
    return ["assigned", "submitted", "failed"].includes(data.status);
  }, [data]);

  const onSubmit = async () => {
    if (!file) {
      toast.error("Please choose a video file first.");
      return;
    }

    try {
      const result = await submitVideo.mutateAsync(file);
      setAnalysis(result.analysis || null);
      toast.success("Video submitted and processed successfully.");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Failed to submit video.");
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto py-10 px-4 space-y-4">
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <p className="text-sm text-slate-600">This candidate link is invalid or expired.</p>
      </div>
    );
  }

  const latestAnalysis = analysis || null;

  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="max-w-3xl mx-auto space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Interview Submission</h1>
          <p className="text-sm text-slate-500 mt-1">
            Candidate: {data.candidate_name} · Status: {data.status}
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">Interview</h2>
          <p className="text-sm text-slate-700">{data.interview_title}</p>
          <div className="space-y-2">
            <p className="text-xs font-medium text-slate-600">Questions</p>
            <ol className="list-decimal pl-5 space-y-1 text-sm text-slate-700">
              {data.questions.map((item) => (
                <li key={item.id}>{item.question}</li>
              ))}
            </ol>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-900">Upload your interview video</h2>
          <p className="text-xs text-slate-500">
            Record your answers to all listed questions and upload one video file.
          </p>

          <div className="flex items-center gap-2">
            <Input
              type="file"
              accept="video/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={!canSubmit || submitVideo.isPending}
            />
            <Button
              onClick={onSubmit}
              disabled={!canSubmit || submitVideo.isPending || !file}
              className="bg-slate-900 hover:bg-slate-700 text-white"
            >
              {submitVideo.isPending ? "Processing..." : "Submit"}
            </Button>
          </div>

          {file && (
            <div className="inline-flex items-center gap-2 text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5">
              <FileVideo className="w-3.5 h-3.5" />
              {file.name}
            </div>
          )}

          {!canSubmit && (
            <p className="text-xs text-slate-500">Submission is closed for this assignment.</p>
          )}
        </div>

        {latestAnalysis && (
          <div className="bg-white border border-slate-200 rounded-2xl p-5 space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <h2 className="text-sm font-semibold text-slate-900">Processed Result</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl border border-slate-200 p-3">
                <p className="text-xs text-slate-500">Decision</p>
                <p className="font-semibold text-slate-900">{latestAnalysis.decision || "REVIEW"}</p>
              </div>
              <div className="rounded-xl border border-slate-200 p-3">
                <p className="text-xs text-slate-500">Overall Score</p>
                <p className="font-semibold text-slate-900">{latestAnalysis.overall_score ?? 0}</p>
              </div>
            </div>
            <p className="text-sm text-slate-700">{latestAnalysis.hr_summary || "Your interview has been processed."}</p>
          </div>
        )}
      </div>
    </div>
  );
}
