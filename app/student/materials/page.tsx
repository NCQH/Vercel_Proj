"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import MainLayout from "../../../components/app-shell/MainLayout";

type PublicClass = { id: string; name: string; code: string; description?: string };
type MembershipItem = {
  membership_id: string;
  status: "pending" | "approved" | "rejected";
  class?: { id: string; name: string; code: string; description?: string };
};
type ClassFile = {
  file_id: string;
  original_filename: string;
  uploaded_at: string;
  size_bytes: number;
  class_id?: string;
  class_name?: string;
};
type PersonalUpload = { file_id: string; filename: string; uploaded_at: string; size: number };

export default function StudentMaterialsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [publicClasses, setPublicClasses] = useState<PublicClass[]>([]);
  const [memberships, setMemberships] = useState<MembershipItem[]>([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [classFiles, setClassFiles] = useState<ClassFile[]>([]);
  const [personalUploads, setPersonalUploads] = useState<PersonalUpload[]>([]);
  const [deletingFileId, setDeletingFileId] = useState("");
  const [deleteMessage, setDeleteMessage] = useState("");
  const [error, setError] = useState("");

  const identity =
    (session?.user as { id?: string } | undefined)?.id ||
    session?.user?.email ||
    session?.user?.name ||
    "";

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  const loadPublicClasses = async () => {
    if (!identity) return;
    const res = await fetch(`/api/classes/public?user_id=${encodeURIComponent(identity)}`, { cache: "no-store" });
    const data = await res.json();
    console.log("[DEBUG] Public classes loaded:", data.items);
    setPublicClasses(data.items || []);
  };

  const loadMemberships = async () => {
    if (!identity) return [] as MembershipItem[];
    const res = await fetch(`/api/classes?user_id=${encodeURIComponent(identity)}&role=student`, { cache: "no-store" });
    const data = await res.json();
    const items = (data.items || []) as MembershipItem[];
    setMemberships(items);
    const approved = items.find((m: MembershipItem) => m.status === "approved" && m.class?.id);
    const approvedClassId = approved?.class?.id || "";
    if (!selectedClassId && approvedClassId) setSelectedClassId(approvedClassId);
    return items;
  };

  const loadClassFiles = async (classId: string) => {
    if (!identity || !classId) return [] as ClassFile[];
    const res = await fetch(`/api/class-files?user_id=${encodeURIComponent(identity)}&class_id=${encodeURIComponent(classId)}`, { cache: "no-store" });
    if (!res.ok) {
      return [] as ClassFile[];
    }
    const data = await res.json();
    return (data.items || []) as ClassFile[];
  };

  const loadApprovedClassFiles = async (items: MembershipItem[]) => {
    const classNameById = new Map(publicClasses.map((c) => [c.id, c.name]));

    const approvedClasses = items
      .filter((m) => m.status === "approved")
      .map((m) => {
        const raw = m as MembershipItem & {
          class_id?: string;
          class_name?: string;
          class?: { id?: string; name?: string };
        };
        const id = raw.class?.id || raw.class_id || "";
        const name = raw.class?.name || raw.class_name || (id ? classNameById.get(id) : undefined) || "Unknown class";
        return { id, name };
      })
      .filter((c) => Boolean(c.id));

    if (approvedClasses.length === 0) {
      setClassFiles([]);
      return;
    }

    const filesByClass = await Promise.all(
      approvedClasses.map(async (c) => {
        const files = await loadClassFiles(c.id);
        return files.map((f) => ({ ...f, class_id: c.id, class_name: c.name }));
      })
    );
    setClassFiles(filesByClass.flat());
  };

  const loadPersonalUploads = async () => {
    if (!identity) return;
    const res = await fetch(`/api/uploads?user_id=${encodeURIComponent(identity)}`, { cache: "no-store" });
    if (!res.ok) {
      setPersonalUploads([]);
      return;
    }
    const data = await res.json();
    setPersonalUploads(data.items || []);
  };

  useEffect(() => {
    if (status !== "authenticated") return;

    const initData = async () => {
      const [, membershipItems] = await Promise.all([
        loadPublicClasses(),
        loadMemberships(),
      ]);

      await Promise.all([
        loadApprovedClassFiles(membershipItems),
        loadPersonalUploads(),
      ]);
    };

    initData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, identity]);

  useEffect(() => {
    loadApprovedClassFiles(memberships);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memberships]);

  useEffect(() => {
    if (!identity) return;
    const latestUploadedAt = classFiles.reduce((max: number, f) => {
      const t = f.uploaded_at ? new Date(f.uploaded_at).getTime() : 0;
      return t > max ? t : max;
    }, 0);
    if (latestUploadedAt > 0) {
      localStorage.setItem(`student_materials_last_seen_${identity}`, String(latestUploadedAt));
    }
  }, [classFiles, identity]);

  const requestJoin = async (classCode?: string) => {
    const code = (classCode || "").trim().toUpperCase();
    console.log("[DEBUG] requestJoin called with classCode:", classCode, "-> normalized:", code);
    if (!code || !identity) {
      console.error("[DEBUG] Missing code or identity:", { code, identity });
      setError("Invalid class code. Please try again.");
      return;
    }
    setError("");
    const fd = new FormData();
    fd.append("user_id", identity);
    fd.append("class_code", code);
    try {
      const res = await fetch("/api/classes/join", { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      console.log("[DEBUG] Join response:", { status: res.status, data });
      if (!res.ok) {
        const errorMsg = data?.detail || "Join request failed. Please try again.";
        setError(errorMsg);
        return;
      }
      const membershipItems = await loadMemberships();
      await loadApprovedClassFiles(membershipItems);
    } catch (err) {
      console.error("[DEBUG] Join request error:", err);
      setError("Network error. Please check your connection and try again.");
    }
  };

  const deletePersonalUpload = async (fileId: string, filename: string) => {
    if (!identity || !fileId || deletingFileId) return;
    const confirmed = window.confirm(`Delete "${filename}"?\n\nFile will be removed from your uploads and AI retrieval context.`);
    if (!confirmed) return;

    setDeleteMessage("");
    setDeletingFileId(fileId);
    try {
      const res = await fetch(`/api/uploads/${encodeURIComponent(fileId)}?user_id=${encodeURIComponent(identity)}`, {
        method: "DELETE",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setDeleteMessage(data?.detail || "Delete failed. Please try again.");
        return;
      }
      setDeleteMessage(`Deleted ${filename}. AI will no longer retrieve this file.`);
      await loadPersonalUploads();
    } catch {
      setDeleteMessage("Delete failed due to network error.");
    } finally {
      setDeletingFileId("");
    }
  };

  if (status === "loading") return <MainLayout role="student"><div className="p-8">Loading...</div></MainLayout>;

  return (
    <MainLayout role="student">
      <section className="mx-auto w-full max-w-6xl space-y-6">
        <div className="rounded-3xl border border-slate-200 bg-white p-6">
          <h1 className="text-3xl font-semibold text-slate-900">Class Materials</h1>
          <p className="mt-2 text-sm text-slate-600">Join classes and access approved class files.</p>
          {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-slate-900">Available Classes</h2>
            <div className="mt-3 space-y-2">
              {publicClasses.map((c) => {
                const isApproved = memberships.some((m) => m.status === "approved" && m.class?.id === c.id);
                const isPending = memberships.some((m) => m.status === "pending" && m.class?.id === c.id);
                return (
                <div key={c.id} className="rounded-[24px] border border-slate-200 p-5 shadow-[0_2px_8px_rgba(15,23,42,0.04)] hover:shadow-md transition">
                  <div className="flex justify-between items-start gap-4">
                     <div>
                       <h3 className="font-bold text-slate-900 text-lg">{c.name}</h3>
                       <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs font-bold text-brand-600 bg-brand-50 px-2 py-0.5 rounded-md">{c.code}</span>
                          <span className="text-xs text-slate-500">• {c.description || "Instructor / Details"}</span>
                       </div>
                     </div>
                     {!isApproved && !isPending ? (
                       <button id={`request-join-${c.id}`} onClick={() => requestJoin(c.code)} className="shrink-0 rounded-xl bg-slate-900 hover:bg-slate-800 px-4 py-2 text-xs font-bold text-white transition shadow-sm">Join Class</button>
                     ) : isPending ? (
                       <span className="shrink-0 rounded-xl bg-amber-50 text-amber-700 px-4 py-2 text-xs font-bold border border-amber-200">Pending</span>
                     ) : (
                       <span className="shrink-0 rounded-xl bg-emerald-50 text-emerald-700 px-4 py-2 text-xs font-bold border border-emerald-200">Joined ✓</span>
                     )}
                  </div>
                </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-slate-900">My Memberships</h2>
            <div className="mt-3 space-y-2">
              {memberships.map((m) => (
                <button key={m.membership_id} id={`membership-${m.membership_id}`} onClick={() => m.class?.id && setSelectedClassId(m.class.id)} className={`w-full flex items-center justify-between rounded-[20px] border px-4 py-3 text-left transition hover:shadow-md ${selectedClassId === m.class?.id ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
                  <div>
                     <div className="font-bold text-slate-900">{m.class?.name || "Unknown class"}</div>
                     <div className="text-[11px] uppercase tracking-wider font-bold text-slate-500 mt-1">Status: <span className={`${m.status === 'approved' ? 'text-emerald-600' : 'text-amber-600'}`}>{m.status}</span></div>
                  </div>
                  {selectedClassId === m.class?.id && <div className="h-2 w-2 rounded-full bg-brand-600"></div>}
                </button>
              ))}
              {memberships.length === 0 && <p className="text-sm text-slate-500 p-4 text-center">You haven't joined any classes yet.</p>}
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6">
          <h2 className="text-xl font-semibold text-slate-900">Approved Class Files</h2>
          <div className="mt-3 space-y-2">
            {classFiles.map((f) => (
              <div key={`${f.class_id || "no-class"}-${f.file_id}`} className="group flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 px-4 py-3 hover:bg-slate-50 transition shadow-[0_2px_8px_rgba(15,23,42,0.02)]">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                  </div>
                  <div>
                    <div className="font-bold text-slate-900 text-sm">{f.original_filename}</div>
                    <div className="text-[11px] text-slate-500 mt-0.5 uppercase tracking-wider font-bold">Class: {f.class_name || "Unknown class"}</div>
                  </div>
                </div>
                <a id={`download-class-file-${f.file_id}`} href={`/api/class-files/download?user_id=${encodeURIComponent(identity)}&file_id=${encodeURIComponent(f.file_id)}`} className="text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 px-4 py-2 rounded-xl transition sm:opacity-0 sm:group-hover:opacity-100 text-center shrink-0">Download</a>
              </div>
            ))}
            {classFiles.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center rounded-[24px] border border-dashed border-slate-300 bg-slate-50">
                <div className="text-4xl mb-3">📂</div>
                <h3 className="font-bold text-slate-900 text-lg mb-1">No materials yet</h3>
                <p className="text-sm text-slate-500 max-w-sm px-4">Join a class above to access lecture slides, practice exercises, and exam reviews.</p>
              </div>
            ) : null}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">My Uploaded Files</h2>
              <p className="mt-1 text-xs text-slate-500">Delete files you no longer want AI to use for retrieval.</p>
            </div>
            {deletingFileId ? <span className="text-xs font-bold text-rose-600">Deleting...</span> : null}
          </div>
          {deleteMessage ? (
            <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-700">
              {deleteMessage}
            </div>
          ) : null}
          <div className="mt-3 space-y-2">
            {personalUploads.map((f) => {
              const busy = deletingFileId === f.file_id;
              return (
                <div key={f.file_id} className="group flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3 hover:bg-slate-50 transition shadow-[0_2px_8px_rgba(15,23,42,0.02)]">
                  <span className="font-bold text-slate-900 text-sm truncate">{f.filename}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <a id={`download-personal-file-${f.file_id}`} href={`/api/uploads/download?user_id=${encodeURIComponent(identity)}&file_id=${encodeURIComponent(f.file_id)}`} className="text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 px-3 py-1.5 rounded-lg transition opacity-0 group-hover:opacity-100">Download</a>
                    <button
                      id={`delete-personal-file-${f.file_id}`}
                      onClick={() => deletePersonalUpload(f.file_id, f.filename)}
                      disabled={Boolean(deletingFileId)}
                      className={`text-xs font-bold px-3 py-1.5 rounded-lg transition ${busy ? "bg-rose-100 text-rose-500 cursor-not-allowed" : "bg-rose-50 text-rose-700 hover:bg-rose-100"}`}
                    >
                      {busy ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </div>
              );
            })}
            {personalUploads.length === 0 ? <p className="text-sm text-slate-500 font-medium px-2">No personal uploaded files yet.</p> : null}
          </div>
        </div>
      </section>
    </MainLayout>
  );
}
