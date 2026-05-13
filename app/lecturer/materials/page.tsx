"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import { apiClient, type ClassFile, type ClassMembership, type ClassSummary } from "../../../lib/api-client";
import MainLayout from "../../../components/app-shell/MainLayout";

type ClassItem = Required<Pick<ClassSummary, "id" | "name" | "code">> & Pick<ClassSummary, "description">;
type PendingItem = ClassMembership & { id: string; class_id: string; student_id: string; status: string; requested_at: string };

export default function LecturerMaterialsPage() {
  const { data: session } = useSession();
  const fileRef = useRef<HTMLInputElement>(null);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [classFiles, setClassFiles] = useState<ClassFile[]>([]);
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [deletingFileId, setDeletingFileId] = useState("");
  const [fileActionMessage, setFileActionMessage] = useState("");

  const identity = (session?.user as { id?: string } | undefined)?.id || session?.user?.email || session?.user?.name || "";

  const loadClasses = async () => {
    if (!identity) return;
    try {
      const data = await apiClient.classes.list("lecturer");
      const items = (data.items || []) as ClassItem[];
      setClasses(items);
      if (!selectedClassId && items[0]?.id) setSelectedClassId(items[0].id);
    } catch (err) {
      console.error("Failed to load classes", err);
    }
  };

  const loadPending = async (classId: string) => {
    if (!identity) return;
    try {
      const data = await apiClient.classes.listPendingRequests(classId);
      setPending((data.items || []) as PendingItem[]);
    } catch (err) {
      console.error("Failed to load pending requests", err);
    }
  };

  const loadFiles = async (classId: string) => {
    if (!identity) return;
    try {
      const data = await apiClient.classes.listFiles(classId);
      setClassFiles(data.items || []);
    } catch (err) {
      console.error("Failed to load files", err);
    }
  };

  useEffect(() => { loadClasses(); }, [identity]);
  useEffect(() => {
    if (!selectedClassId) return;
    loadPending(selectedClassId);
    loadFiles(selectedClassId);
  }, [selectedClassId]);

  const createClass = async () => {
    try {
      await apiClient.classes.create(name, description);
      setName("");
      setDescription("");
      await loadClasses();
    } catch (err) {
      console.error("Failed to create class", err);
    }
  };

  const approve = async (id: string, ok: boolean) => {
    try {
      await apiClient.classes.approveRequest(id, ok);
      await loadPending(selectedClassId);
    } catch (err) {
      console.error("Failed to approve/reject", err);
    }
  };

  const uploadClassFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = fileRef.current?.files?.[0];
    if (!file || !selectedClassId) return;
    setFileActionMessage("");
    try {
      await apiClient.classes.uploadFile(selectedClassId, file);
      setFileActionMessage(`Uploaded ${file.name} successfully.`);
      await loadFiles(selectedClassId);
    } catch (err) {
      console.error("Upload failed", err);
      setFileActionMessage("Upload failed. Please try again.");
    }
    e.target.value = "";
  };

  const deleteClassFile = async (fileId: string, filename: string) => {
    if (!identity || !selectedClassId) return;
    const confirmed = window.confirm(
      `Delete \"${filename}\"?\n\nFile will be removed from class materials and AI retrieval context.`
    );
    if (!confirmed) return;

    setDeletingFileId(fileId);
    setFileActionMessage("");
    try {
      await apiClient.classes.deleteClassFile(fileId);
      setFileActionMessage(`Deleted ${filename} successfully.`);
      await loadFiles(selectedClassId);
    } catch (err) {
      console.error("Delete failed", err);
      setFileActionMessage("Delete failed due to network error.");
    } finally {
      setDeletingFileId("");
    }
  };

  return (
    <MainLayout role="lecturer">
      <section className="mx-auto w-full max-w-6xl space-y-6">
        <div className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
          <h1 className="text-2xl font-bold text-slate-900">Class Management</h1>
          <p className="mt-1 text-sm text-slate-500">Create new classes and manage your existing ones.</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_2fr_auto]">
            <input id="class-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Class name" className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:bg-white focus:ring-1 focus:ring-brand-500 transition" />
            <input id="class-desc-input" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Description" className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:bg-white focus:ring-1 focus:ring-brand-500 transition" />
            <button id="create-class-btn" onClick={createClass} className="rounded-xl bg-brand-600 hover:bg-brand-700 px-6 py-2.5 text-sm font-bold text-white transition shadow-sm disabled:opacity-50" disabled={!name.trim()}>Create Class</button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
            <h2 className="font-bold text-lg text-slate-900">Your Classes</h2>
            <div className="mt-4 space-y-2">
              {classes.map((c) => (
                <button id={`lecturer-class-${c.id}`} key={c.id} onClick={() => setSelectedClassId(c.id)} className={`w-full flex items-center justify-between rounded-[20px] border px-4 py-3 text-left transition hover:shadow-md ${selectedClassId === c.id ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
                  <div>
                    <div className="font-bold text-slate-900">{c.name}</div>
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mt-1">Code: <span className="text-brand-600">{c.code}</span></div>
                  </div>
                  {selectedClassId === c.id && <div className="h-2 w-2 rounded-full bg-brand-600"></div>}
                </button>
              ))}
              {classes.length === 0 && <p className="text-sm font-medium text-slate-500 bg-slate-50 p-4 rounded-xl text-center border border-dashed border-slate-200">No classes created yet.</p>}
            </div>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
            <h2 className="font-bold text-lg text-slate-900">Pending Requests</h2>
            <div className="mt-4 space-y-3">
              {pending.map((p) => (
                <div key={p.id} className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 rounded-2xl border border-slate-200 p-4 shadow-[0_2px_8px_rgba(15,23,42,0.02)] hover:bg-slate-50 transition">
                  <div>
                     <div className="text-sm font-bold text-slate-900">Student ID: {p.student_id}</div>
                     <div className="text-xs font-medium text-slate-500 mt-1">Status: {p.status}</div>
                  </div>
                  {p.status === "pending" ? (
                    <div className="flex gap-2 shrink-0">
                      <button id={`approve-${p.id}`} onClick={() => approve(p.id, true)} className="rounded-xl bg-emerald-600 hover:bg-emerald-700 px-4 py-2 text-xs font-bold text-white transition shadow-sm">Approve</button>
                      <button id={`reject-${p.id}`} onClick={() => approve(p.id, false)} className="rounded-xl bg-rose-600 hover:bg-rose-700 px-4 py-2 text-xs font-bold text-white transition shadow-sm">Reject</button>
                    </div>
                  ) : (
                    <span className={`shrink-0 rounded-xl px-4 py-2 text-xs font-bold border ${p.status === "approved" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-slate-100 text-slate-600 border-slate-200"}`}>
                      {p.status === "approved" ? "Approved" : "Processed"}
                    </span>
                  )}
                </div>
              ))}
              {pending.length === 0 ? <p className="text-sm font-medium text-slate-500 bg-slate-50 p-4 rounded-xl text-center border border-dashed border-slate-200">No pending requests.</p> : null}
            </div>
          </div>
        </div>

        <div className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
          <div className="flex flex-wrap items-center justify-between gap-4">
             <h2 className="font-bold text-lg text-slate-900">Class Files</h2>
             <button id="upload-class-file-btn" onClick={() => fileRef.current?.click()} className="rounded-xl bg-slate-900 hover:bg-slate-800 px-5 py-2.5 text-sm font-bold text-white transition shadow-sm">Upload Material</button>
          </div>
          <input ref={fileRef} type="file" accept=".pdf,.docx" className="hidden" onChange={uploadClassFile} />
          {fileActionMessage ? (
            <p className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700">
              {fileActionMessage}
            </p>
          ) : null}
          <div className="mt-5 space-y-2">
            {classFiles.map((f) => (
              <div key={f.file_id} className="group flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 px-4 py-3 hover:bg-slate-50 transition shadow-[0_2px_8px_rgba(15,23,42,0.02)]">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                  </div>
                  <div>
                    <div className="font-bold text-slate-900 text-sm">{f.original_filename}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5 font-medium">Uploaded: {f.uploaded_at ? new Date(f.uploaded_at).toLocaleDateString() : "Unknown"}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <a id={`download-class-file-${f.file_id}`} href={`/api/class-files/download?file_id=${encodeURIComponent(f.file_id)}`} className="text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 px-4 py-2 rounded-xl transition sm:opacity-0 sm:group-hover:opacity-100 text-center">Download</a>
                  <button
                    id={`delete-class-file-${f.file_id}`}
                    onClick={() => deleteClassFile(f.file_id, f.original_filename)}
                    disabled={deletingFileId === f.file_id}
                    className="text-xs font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 px-4 py-2 rounded-xl transition disabled:opacity-60"
                  >
                    {deletingFileId === f.file_id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
            ))}
            {classFiles.length === 0 ? (
               <div className="flex flex-col items-center justify-center py-10 text-center rounded-[24px] border border-dashed border-slate-300 bg-slate-50">
                <div className="text-4xl mb-3">📂</div>
                <h3 className="font-bold text-slate-900 text-lg mb-1">No files uploaded</h3>
                <p className="text-sm text-slate-500 max-w-sm px-4">Upload materials above to share with your students.</p>
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </MainLayout>
  );
}
