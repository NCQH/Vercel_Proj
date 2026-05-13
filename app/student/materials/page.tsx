"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import MainLayout from "../../../components/app-shell/MainLayout";
import { apiClient, ApiError, type ClassFile, type ClassMembership, type ClassSummary, type UploadItem } from "../../../lib/api-client";
import { useToast } from "../../../components/ui/ToastProvider";

type PublicClass = Required<Pick<ClassSummary, "id" | "name" | "code">> & Pick<ClassSummary, "description">;
type MembershipItem = Required<Pick<ClassMembership, "membership_id" | "status">> & { class?: PublicClass };
type PersonalUpload = UploadItem & { filename: string };

export default function StudentMaterialsPage() {
  const { data: session, status } = useSession();
  const { showToast } = useToast();
  const router = useRouter();

  const [publicClasses, setPublicClasses] = useState<PublicClass[]>([]);
  const [memberships, setMemberships] = useState<MembershipItem[]>([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [classFiles, setClassFiles] = useState<ClassFile[]>([]);
  const [personalUploads, setPersonalUploads] = useState<PersonalUpload[]>([]);
  const [deletingFileId, setDeletingFileId] = useState("");
  const [joiningClassId, setJoiningClassId] = useState("");
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isClassFilesLoading, setIsClassFilesLoading] = useState(false);
  const [classFileSearch, setClassFileSearch] = useState("");
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
    const data = await apiClient.classes.listPublic();
    setPublicClasses((data.items || []) as PublicClass[]);
  };

  const loadMemberships = async () => {
    if (!identity) return [] as MembershipItem[];
    const data = await apiClient.classes.list("student");
    const items = (data.items || []) as MembershipItem[];
    setMemberships(items);
    const approved = items.find((m: MembershipItem) => m.status === "approved" && m.class?.id);
    const approvedClassId = approved?.class?.id || "";
    if (!selectedClassId && approvedClassId) setSelectedClassId(approvedClassId);
    return items;
  };

  const loadApprovedClassFiles = async () => {
    if (!identity) {
      setClassFiles([]);
      return;
    }

    setIsClassFilesLoading(true);
    try {
      const data = await apiClient.classes.listApprovedFiles();
      setClassFiles((data.items || []) as ClassFile[]);
    } finally {
      setIsClassFilesLoading(false);
    }
  };

  const loadPersonalUploads = async () => {
    if (!identity) return;
    try {
      const data = await apiClient.uploads.list();
      setPersonalUploads((data.items || []) as PersonalUpload[]);
    } catch {
      setPersonalUploads([]);
    }
  };

  useEffect(() => {
    if (status !== "authenticated") return;

    const initData = async () => {
      setIsInitialLoading(true);
      try {
        await Promise.all([
          loadPublicClasses(),
          loadMemberships(),
        ]);

        await Promise.all([
          loadApprovedClassFiles(),
          loadPersonalUploads(),
        ]);
      } finally {
        setIsInitialLoading(false);
      }
    };

    initData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, identity]);

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

  const requestJoin = async (targetClass?: PublicClass) => {
    const code = (targetClass?.code || "").trim().toUpperCase();
    if (!code || !identity || !targetClass?.id || joiningClassId) {
      setError("Invalid class code. Please try again.");
      showToast({ type: "warning", title: "Invalid class", message: "Please choose a valid class before joining." });
      return;
    }

    setError("");
    setJoiningClassId(targetClass.id);

    const optimisticMembershipId = `optimistic-${targetClass.id}`;
    setMemberships((prev) => {
      const existed = prev.some((m) => m.class?.id === targetClass.id);
      if (existed) return prev;
      return [
        {
          membership_id: optimisticMembershipId,
          status: "pending",
          class: {
            id: targetClass.id,
            name: targetClass.name,
            code: targetClass.code,
            description: targetClass.description,
          },
        },
        ...prev,
      ];
    });


    try {
      await apiClient.classes.join(code);
      await loadMemberships();
      await loadApprovedClassFiles();
      showToast({ type: "success", title: "Join request sent", message: `${targetClass.name} is waiting for lecturer approval.` });
    } catch (err) {
      setMemberships((prev) => prev.filter((m) => m.membership_id !== optimisticMembershipId));
      const message = err instanceof ApiError ? err.message : "Network error. Please check your connection and try again.";
      setError(message);
      showToast({ type: "error", title: "Join failed", message });
    } finally {
      setJoiningClassId("");
    }
  };

  const deletePersonalUpload = async (fileId: string, filename: string) => {
    if (!identity || !fileId || deletingFileId) return;
    const confirmed = window.confirm(`Delete \"${filename}\"?\n\nFile will be removed from your uploads and AI retrieval context.`);
    if (!confirmed) return;

    setDeleteMessage("");
    setDeletingFileId(fileId);
    try {
      await apiClient.uploads.delete(fileId);
      setDeleteMessage(`Deleted ${filename}. AI will no longer retrieve this file.`);
      showToast({ type: "success", title: "File deleted", message: filename });
      await loadPersonalUploads();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Delete failed due to network error.";
      setDeleteMessage(message);
      showToast({ type: "error", title: "Delete failed", message });
    } finally {
      setDeletingFileId("");
    }
  };

  const selectedClass = memberships.find((m) => m.class?.id === selectedClassId)?.class;
  const visibleClassFiles = classFiles.filter((file) => {
    const matchesClass = selectedClassId ? file.class_id === selectedClassId : true;
    const query = classFileSearch.trim().toLowerCase();
    const matchesSearch = !query || [file.original_filename, file.class_name]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
    return matchesClass && matchesSearch;
  });

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
              {isInitialLoading ? (
                Array.from({ length: 3 }).map((_, idx) => (
                  <div key={`class-skeleton-${idx}`} className="animate-pulse rounded-[24px] border border-slate-200 p-5">
                    <div className="h-5 w-40 rounded bg-slate-200" />
                    <div className="mt-2 h-4 w-52 rounded bg-slate-100" />
                  </div>
                ))
              ) : publicClasses.map((c) => {
                const isApproved = memberships.some((m) => m.status === "approved" && m.class?.id === c.id);
                const isPending = memberships.some((m) => m.status === "pending" && m.class?.id === c.id);
                const isJoining = joiningClassId === c.id;
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
                       <button id={`request-join-${c.id}`} onClick={() => requestJoin(c)} disabled={Boolean(joiningClassId)} className="shrink-0 rounded-xl bg-slate-900 hover:bg-slate-800 px-4 py-2 text-xs font-bold text-white transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed">{isJoining ? "Sending..." : "Join Class"}</button>
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
              {isInitialLoading ? (
                Array.from({ length: 2 }).map((_, idx) => (
                  <div key={`member-skeleton-${idx}`} className="animate-pulse rounded-[20px] border border-slate-200 px-4 py-3">
                    <div className="h-4 w-36 rounded bg-slate-200" />
                    <div className="mt-2 h-3 w-24 rounded bg-slate-100" />
                  </div>
                ))
              ) : memberships.map((m) => (
                <button key={m.membership_id} id={`membership-${m.membership_id}`} onClick={() => m.class?.id && setSelectedClassId(m.class.id)} className={`w-full flex items-center justify-between rounded-[20px] border px-4 py-3 text-left transition hover:shadow-md ${selectedClassId === m.class?.id ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500' : 'border-slate-200 bg-white hover:border-slate-300'}`}>
                  <div>
                     <div className="font-bold text-slate-900">{m.class?.name || "Unknown class"}</div>
                     <div className="text-[11px] uppercase tracking-wider font-bold text-slate-500 mt-1">Status: <span className={`${m.status === 'approved' ? 'text-emerald-600' : 'text-amber-600'}`}>{m.status}</span></div>
                  </div>
                  {selectedClassId === m.class?.id && <div className="h-2 w-2 rounded-full bg-brand-600"></div>}
                </button>
              ))}
              {!isInitialLoading && memberships.length === 0 && <p className="text-sm text-slate-500 p-4 text-center">You haven't joined any classes yet.</p>}
            </div>
          </div>
        </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                {selectedClass ? `${selectedClass.name} Files` : "Approved Class Files"}
              </h2>
              <p className="mt-1 text-xs text-slate-500">
                {selectedClass ? "Showing files from selected class." : "Select an approved class to filter files."}
              </p>
            </div>
            <input
              id="class-file-search"
              value={classFileSearch}
              onChange={(event) => setClassFileSearch(event.target.value)}
              placeholder="Search files..."
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:bg-white focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div className="mt-3 space-y-2">
            {isClassFilesLoading ? (
              Array.from({ length: 3 }).map((_, idx) => (
                <div key={`file-skeleton-${idx}`} className="animate-pulse flex items-center justify-between rounded-2xl border border-slate-200 px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-slate-200" />
                    <div>
                      <div className="h-4 w-40 rounded bg-slate-200" />
                      <div className="mt-2 h-3 w-28 rounded bg-slate-100" />
                    </div>
                  </div>
                  <div className="h-8 w-20 rounded-xl bg-slate-100" />
                </div>
              ))
            ) : visibleClassFiles.map((f) => (
              <div key={`${f.class_id || "no-class"}-${f.file_id}`} className="group flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-slate-200 px-4 py-3 hover:bg-slate-50 transition shadow-[0_2px_8px_rgba(15,23,42,0.02)]">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                  </div>
                  <div>
                    <div className="font-bold text-slate-900 text-sm">{f.original_filename}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="text-[11px] text-slate-500 uppercase tracking-wider font-bold">Class: {f.class_name || "Unknown class"}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-wider ${f.ingest_status === "failed" ? "bg-rose-50 text-rose-700" : f.ingest_status === "ready" || !f.ingest_status ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                        {f.ingest_status || "ready"}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <a id={`download-class-file-${f.file_id}`} href={`/api/class-files/download?file_id=${encodeURIComponent(f.file_id)}`} className="text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 px-4 py-2 rounded-xl transition text-center">Download</a>
                </div>
              </div>
            ))}
            {!isClassFilesLoading && visibleClassFiles.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center rounded-[24px] border border-dashed border-slate-300 bg-slate-50">
                <div className="text-4xl mb-3">📂</div>
                <h3 className="font-bold text-slate-900 text-lg mb-1">No matching materials</h3>
                <p className="text-sm text-slate-500 max-w-sm px-4">Try another class or search term, or wait for your lecturer to upload materials.</p>
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
                  <div className="min-w-0">
                    <span className="block truncate font-bold text-slate-900 text-sm">{f.filename}</span>
                    <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-wider ${f.ingest_status === "failed" ? "bg-rose-50 text-rose-700" : f.ingest_status === "ready" || !f.ingest_status ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                      {f.ingest_status || "ready"}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <a id={`download-personal-file-${f.file_id}`} href={`/api/uploads/download?file_id=${encodeURIComponent(f.file_id)}`} className="text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 px-3 py-1.5 rounded-lg transition">Download</a>
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
