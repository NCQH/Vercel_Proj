"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import MainLayout from "../../../components/app-shell/MainLayout";

type ClassItem = { id: string; name: string; code: string; description?: string };
type PendingItem = { id: string; class_id: string; student_id: string; status: string; requested_at: string };
type ClassFile = { file_id: string; original_filename: string; size_bytes: number; uploaded_at: string };

export default function LecturerMaterialsPage() {
  const { data: session } = useSession();
  const fileRef = useRef<HTMLInputElement>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [classFiles, setClassFiles] = useState<ClassFile[]>([]);
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const identity = (session?.user as { id?: string } | undefined)?.id || session?.user?.email || session?.user?.name || "";

  const loadClasses = async () => {
    if (!identity) return;
    const res = await fetch(`/api/classes?user_id=${encodeURIComponent(identity)}&role=lecturer`, { cache: "no-store" });
    const data = await res.json();
    const items = data.items || [];
    setClasses(items);
    if (!selectedClassId && items[0]?.id) setSelectedClassId(items[0].id);
  };

  const loadPending = async (classId: string) => {
    if (!identity) return;
    const res = await fetch(`/api/classes/pending?user_id=${encodeURIComponent(identity)}&class_id=${encodeURIComponent(classId)}`, { cache: "no-store" });
    const data = await res.json();
    setPending(data.items || []);
  };

  const loadFiles = async (classId: string) => {
    if (!identity) return;
    const res = await fetch(`/api/class-files?user_id=${encodeURIComponent(identity)}&class_id=${encodeURIComponent(classId)}`, { cache: "no-store" });
    const data = await res.json();
    setClassFiles(data.items || []);
  };

  useEffect(() => { loadClasses(); }, [identity]);
  useEffect(() => {
    if (!selectedClassId) return;
    loadPending(selectedClassId);
    loadFiles(selectedClassId);
  }, [selectedClassId]);

  const createClass = async () => {
    const fd = new FormData();
    fd.append("user_id", identity);
    fd.append("name", name);
    fd.append("description", description);
    await fetch("/api/classes", { method: "POST", body: fd });
    setName("");
    setDescription("");
    await loadClasses();
  };

  const approve = async (id: string, ok: boolean) => {
    const fd = new FormData();
    fd.append("user_id", identity);
    fd.append("approve", String(ok));
    await fetch(`/api/classes/members/${id}/approve`, { method: "POST", body: fd });
    await loadPending(selectedClassId);
  };

  const uploadClassFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedClassId) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("user_id", identity);
    fd.append("class_id", selectedClassId);
    await fetch("/api/class-files/upload", { method: "POST", body: fd });
    await loadFiles(selectedClassId);
    e.target.value = "";
  };

  return (
    <MainLayout role="lecturer">
      <section className="mx-auto w-full max-w-6xl space-y-6">
        <div className="rounded-3xl border border-slate-200 bg-white p-6">
          <h1 className="text-2xl font-semibold">Class Management</h1>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <input id="class-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Class name" className="rounded-xl border px-3 py-2" />
            <input id="class-desc-input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" className="rounded-xl border px-3 py-2" />
            <button id="create-class-btn" onClick={createClass} className="rounded-xl bg-brand-600 px-4 py-2 font-semibold text-white">Create</button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-3xl border bg-white p-6">
            <h2 className="font-semibold">Your Classes</h2>
            <div className="mt-3 space-y-2">
              {classes.map((c) => (
                <button id={`lecturer-class-${c.id}`} key={c.id} onClick={() => setSelectedClassId(c.id)} className="w-full rounded-xl border px-3 py-2 text-left">
                  <div className="font-medium">{c.name}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-3xl border bg-white p-6">
            <h2 className="font-semibold">Pending Requests</h2>
            <div className="mt-3 space-y-2">
              {pending.map((p) => (
                <div key={p.id} className="rounded-xl border px-3 py-2">
                  <div className="text-sm">Student: {p.student_id}</div>
                  <div className="mt-2 flex gap-2">
                    <button id={`approve-${p.id}`} onClick={() => approve(p.id, true)} className="rounded-lg bg-emerald-600 px-3 py-1 text-xs text-white">Approve</button>
                    <button id={`reject-${p.id}`} onClick={() => approve(p.id, false)} className="rounded-lg bg-rose-600 px-3 py-1 text-xs text-white">Reject</button>
                  </div>
                </div>
              ))}
              {pending.length === 0 ? <p className="text-sm text-slate-500">No pending requests.</p> : null}
            </div>
          </div>
        </div>

        <div className="rounded-3xl border bg-white p-6">
          <h2 className="font-semibold">Class Files</h2>
          <button id="upload-class-file-btn" onClick={() => fileRef.current?.click()} className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white">Upload file</button>
          <input ref={fileRef} type="file" className="hidden" onChange={uploadClassFile} />
          <div className="mt-3 space-y-2">
            {classFiles.map((f) => (
              <div key={f.file_id} className="flex items-center justify-between rounded-xl border px-3 py-2">
                <span>{f.original_filename}</span>
                <a id={`download-class-file-${f.file_id}`} href={`/api/class-files/download?user_id=${encodeURIComponent(identity)}&file_id=${encodeURIComponent(f.file_id)}`}>Download</a>
              </div>
            ))}
          </div>
        </div>
      </section>
    </MainLayout>
  );
}
