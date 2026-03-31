import { useMemo, useState } from "react";
import { Plus, Pencil, Trash2, Check, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  useCreateSoftskill,
  useDeleteSoftskill,
  useSoftskillsBank,
  useUpdateSoftskill,
} from "../hooks/useSoftskills";

function SkillRow({ item }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    key: item.key,
    language: item.language,
    display_name: item.display_name,
    description: item.description,
    active: item.active,
  });

  const updateSkill = useUpdateSoftskill();
  const deleteSkill = useDeleteSoftskill();

  const save = async () => {
    try {
      await updateSkill.mutateAsync({ softskillId: item.id, payload: form });
      setEditing(false);
      toast.success("Soft skill updated");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Failed to update soft skill");
    }
  };

  const remove = async () => {
    try {
      await deleteSkill.mutateAsync(item.id);
      toast.success("Soft skill deleted");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Failed to delete soft skill");
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      {editing ? (
        <div className="space-y-2">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
            <Input
              value={form.key}
              onChange={(event) => setForm((prev) => ({ ...prev, key: event.target.value }))}
              placeholder="key"
              className="h-8 text-xs"
            />
            <Input
              value={form.display_name}
              onChange={(event) => setForm((prev) => ({ ...prev, display_name: event.target.value }))}
              placeholder="display name"
              className="h-8 text-xs"
            />
            <select
              value={form.language}
              onChange={(event) => setForm((prev) => ({ ...prev, language: event.target.value }))}
              className="h-8 rounded-md border border-slate-200 bg-white px-2 text-xs"
            >
              <option value="en">English</option>
              <option value="fr">Français</option>
            </select>
          </div>
          <Textarea
            value={form.description}
            onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
            rows={3}
            className="text-xs"
          />
          <label className="inline-flex items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={form.active}
              onChange={(event) => setForm((prev) => ({ ...prev, active: event.target.checked }))}
            />
            Active
          </label>
          <div className="flex gap-2">
            <Button size="sm" className="h-7 text-xs" onClick={save}>
              <Check className="w-3.5 h-3.5 mr-1" /> Save
            </Button>
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setEditing(false)}>
              <X className="w-3.5 h-3.5 mr-1" /> Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700">{item.key}</span>
              <span className="rounded border border-slate-200 px-2 py-0.5 text-[11px] text-slate-600 uppercase">{item.language}</span>
              <span className={`rounded px-2 py-0.5 text-[11px] ${item.active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                {item.active ? "Active" : "Inactive"}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setEditing(true)}>
                <Pencil className="w-3.5 h-3.5" />
              </Button>
              <Button size="icon" variant="ghost" className="h-7 w-7 text-red-500" onClick={remove}>
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
          <p className="text-sm font-medium text-slate-800">{item.display_name}</p>
          <p className="text-xs text-slate-600 leading-relaxed">{item.description}</p>
        </div>
      )}
    </div>
  );
}

export default function SoftskillsPage() {
  const [language, setLanguage] = useState("en");
  const [showInactive, setShowInactive] = useState(false);

  const { data: skills = [], isLoading } = useSoftskillsBank({
    language,
    active: showInactive ? undefined : true,
  });

  const createSkill = useCreateSoftskill();
  const [createForm, setCreateForm] = useState({
    key: "",
    language: "en",
    display_name: "",
    description: "",
    active: true,
  });

  const sorted = useMemo(
    () => [...skills].sort((a, b) => a.key.localeCompare(b.key)),
    [skills]
  );

  const create = async () => {
    try {
      await createSkill.mutateAsync(createForm);
      setCreateForm({ key: "", language, display_name: "", description: "", active: true });
      toast.success("Soft skill created");
    } catch (error) {
      toast.error(error?.response?.data?.detail || "Failed to create soft skill");
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Soft Skills Bank</h1>
        <p className="text-sm text-slate-500 mt-1">
          Recruiters can manage bilingual competency definitions used by AI analysis.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
        <h2 className="text-sm font-semibold text-slate-800">Add Soft Skill</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <Input
            value={createForm.key}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, key: event.target.value }))}
            placeholder="Key (e.g. communication)"
            className="h-8 text-xs"
          />
          <Input
            value={createForm.display_name}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, display_name: event.target.value }))}
            placeholder="Display name"
            className="h-8 text-xs"
          />
          <select
            value={createForm.language}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, language: event.target.value }))}
            className="h-8 rounded-md border border-slate-200 bg-white px-2 text-xs"
          >
            <option value="en">English</option>
            <option value="fr">Français</option>
          </select>
        </div>
        <Textarea
          value={createForm.description}
          onChange={(event) => setCreateForm((prev) => ({ ...prev, description: event.target.value }))}
          rows={3}
          placeholder="Description used by AI classifier"
          className="text-xs"
        />
        <div className="flex items-center justify-between">
          <label className="inline-flex items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={createForm.active}
              onChange={(event) => setCreateForm((prev) => ({ ...prev, active: event.target.checked }))}
            />
            Active
          </label>
          <Button size="sm" onClick={create} className="h-8 text-xs">
            <Plus className="w-3.5 h-3.5 mr-1" /> Add
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setLanguage("en")}
              className={`h-7 px-3 rounded text-xs border ${language === "en" ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-600 border-slate-200"}`}
            >
              English
            </button>
            <button
              onClick={() => setLanguage("fr")}
              className={`h-7 px-3 rounded text-xs border ${language === "fr" ? "bg-slate-900 text-white border-slate-900" : "bg-white text-slate-600 border-slate-200"}`}
            >
              Français
            </button>
          </div>
          <label className="inline-flex items-center gap-2 text-xs text-slate-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
            />
            Show inactive
          </label>
        </div>

        {isLoading ? (
          <p className="text-sm text-slate-500">Loading soft skills…</p>
        ) : sorted.length === 0 ? (
          <p className="text-sm text-slate-500">No soft skills found for this language.</p>
        ) : (
          <div className="space-y-2">
            {sorted.map((item) => (
              <SkillRow key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
