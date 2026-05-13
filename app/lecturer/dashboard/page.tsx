"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import MainLayout from "../../../components/app-shell/MainLayout";
import { apiClient, ApiError, type ClassFile, type ClassMembership, type ClassSummary, type MembershipStatus } from "../../../lib/api-client";

type ClassItem = Required<Pick<ClassSummary, "id" | "name" | "code">> & Pick<ClassSummary, "description">;
type MemberItem = ClassMembership & {
  id: string;
  class_id: string;
  student_id: string;
  student_name?: string;
  status: MembershipStatus;
};

export default function LecturerDashboardPage() {
  const { data: session, status } = useSession();
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [classFiles, setClassFiles] = useState<ClassFile[]>([]);
  const [filter, setFilter] = useState<"all" | "pending" | "approved" | "rejected">("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const identity =
    (session?.user as { id?: string } | undefined)?.id ||
    session?.user?.email ||
    session?.user?.name ||
    "";

  const loadClasses = async () => {
    if (!identity) return;
    setError("");
    try {
      const data = await apiClient.classes.list("lecturer");
      const items = (data.items || []) as ClassItem[];
      setClasses(items);
      if (!selectedClassId && items[0]?.id) setSelectedClassId(items[0].id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load classes");
    }
  };

  const loadMembers = async (classId: string) => {
    if (!identity || !classId) return;
    setLoading(true);
    setError("");
    try {
      const [memberData, fileData] = await Promise.all([
        apiClient.classes.listMembers(classId),
        apiClient.classes.listFiles(classId),
      ]);
      setMembers((memberData.items || []) as MemberItem[]);
      setClassFiles((fileData.items || []) as ClassFile[]);
    } catch (err) {
      setMembers([]);
      setClassFiles([]);
      setError(err instanceof ApiError ? err.message : "Failed to load class analytics");
    } finally {
      setLoading(false);
    }
  };

  const updateMemberStatus = async (membershipId: string, approve: boolean) => {
    if (!identity) return;
    setError("");
    try {
      await apiClient.classes.approveRequest(membershipId, approve);
      await loadMembers(selectedClassId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update student status");
    }
  };

  useEffect(() => {
    if (status !== "authenticated") return;
    loadClasses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, identity]);

  useEffect(() => {
    if (!selectedClassId) return;
    loadMembers(selectedClassId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedClassId]);

  const selectedClass = classes.find((c) => c.id === selectedClassId);

  const filteredMembers = useMemo(() => {
    if (filter === "all") return members;
    return members.filter((m) => m.status === filter);
  }, [members, filter]);

  const countBy = (statusKey: "pending" | "approved" | "rejected") =>
    members.filter((m) => m.status === statusKey).length;

  const totalStudents = members.length;
  const pendingCount = countBy("pending");
  const approvedCount = countBy("approved");
  const rejectedCount = countBy("rejected");
  const materialCount = classFiles.length;
  const approvalRate = totalStudents ? Math.round((approvedCount / totalStudents) * 100) : 0;
  const latestMaterial = classFiles
    .slice()
    .sort((a, b) => new Date(b.uploaded_at || 0).getTime() - new Date(a.uploaded_at || 0).getTime())[0];

  return (
    <MainLayout role="lecturer">
      <section className="mx-auto w-full max-w-6xl space-y-6">
        <div className="rounded-[24px] border border-slate-200 bg-white p-8 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
          <p className="text-xs uppercase tracking-[0.2em] font-bold text-brand-600">Lecturer dashboard</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900">Manage your class students</h1>
          <p className="mt-2 text-sm text-slate-600">Choose a class, review student memberships, and approve or reject quickly.</p>
          {error ? <p className="mt-3 text-sm font-semibold text-rose-600 bg-rose-50 px-3 py-2 rounded-xl border border-rose-100 inline-block">{error}</p> : null}
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {[
            { label: "Total students", value: totalStudents, tone: "bg-slate-900 text-white", hint: "All membership records" },
            { label: "Pending", value: pendingCount, tone: "bg-amber-50 text-amber-700 border-amber-100", hint: "Need review" },
            { label: "Approved", value: approvedCount, tone: "bg-emerald-50 text-emerald-700 border-emerald-100", hint: `${approvalRate}% approval rate` },
            { label: "Rejected", value: rejectedCount, tone: "bg-rose-50 text-rose-700 border-rose-100", hint: "Denied requests" },
            { label: "Materials", value: materialCount, tone: "bg-indigo-50 text-indigo-700 border-indigo-100", hint: latestMaterial ? `Latest: ${latestMaterial.original_filename}` : "No files yet" },
          ].map((card) => (
            <div key={card.label} className={`rounded-3xl border p-5 shadow-[0_2px_8px_rgba(15,23,42,0.04)] ${card.tone}`}>
              <p className="text-xs font-black uppercase tracking-[0.18em] opacity-70">{card.label}</p>
              <p className="mt-3 text-3xl font-black">{card.value}</p>
              <p className="mt-2 truncate text-xs font-semibold opacity-75" title={card.hint}>{card.hint}</p>
            </div>
          ))}
        </div>

        <div className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Class attention summary</h2>
              <p className="mt-1 text-sm text-slate-500">Operational signals from current students and uploaded materials.</p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs font-bold">
              {pendingCount > 0 ? <span className="rounded-full bg-amber-50 px-3 py-1.5 text-amber-700">Review {pendingCount} pending request(s)</span> : <span className="rounded-full bg-emerald-50 px-3 py-1.5 text-emerald-700">No pending approvals</span>}
              {materialCount === 0 ? <span className="rounded-full bg-rose-50 px-3 py-1.5 text-rose-700">Upload first material</span> : <span className="rounded-full bg-indigo-50 px-3 py-1.5 text-indigo-700">{materialCount} material(s) available</span>}
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <aside className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
            <h2 className="text-lg font-bold text-slate-900">Your classes</h2>
            <div className="mt-4 space-y-2">
              {classes.map((c) => (
                <button
                  key={c.id}
                  id={`dashboard-class-${c.id}`}
                  onClick={() => setSelectedClassId(c.id)}
                  className={`w-full flex items-center justify-between rounded-[20px] border px-4 py-3 text-left transition hover:shadow-md ${selectedClassId === c.id
                    ? "border-brand-500 bg-brand-50 ring-1 ring-brand-500"
                    : "border-slate-200 bg-white hover:border-slate-300"
                    }`}
                >
                  <div>
                    <div className="font-bold text-slate-900">{c.name}</div>
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 mt-1">Code: <span className="text-brand-600">{c.code}</span></div>
                  </div>
                  {selectedClassId === c.id && <div className="h-2 w-2 rounded-full bg-brand-600"></div>}
                </button>
              ))}
              {classes.length === 0 ? <p className="text-sm font-medium text-slate-500 bg-slate-50 p-4 rounded-xl text-center">No class created yet.</p> : null}
            </div>
          </aside>

          <div className="rounded-[24px] border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">
                  {selectedClass ? `Students in ${selectedClass.name}` : "Select class to manage students"}
                </h2>
                <div className="mt-2 flex flex-wrap gap-2 text-[10px] font-bold uppercase tracking-wider">
                   <span className="text-amber-600 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-100">Pending: {pendingCount}</span>
                   <span className="text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-100">Approved: {approvedCount}</span>
                   <span className="text-rose-600 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-100">Rejected: {rejectedCount}</span>
                </div>
              </div>
              <select
                id="member-status-filter"
                value={filter}
                onChange={(e) => setFilter(e.target.value as "all" | "pending" | "approved" | "rejected")}
                className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-700 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition shadow-sm"
              >
                <option value="all">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <div className="mt-6 space-y-3">
              {loading ? <p className="text-sm font-medium text-slate-500 p-4 text-center">Loading students...</p> : null}

              {!loading && filteredMembers.map((m) => (
                <div key={m.id} className="rounded-2xl border border-slate-200 p-4 hover:bg-slate-50 transition shadow-[0_2px_8px_rgba(15,23,42,0.02)]">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <div className="font-bold text-slate-900 text-lg">
                        {m.full_name || m.student_name || "(Unknown)"}
                      </div>
                      <div className="flex items-center gap-3 mt-1.5">
                        <span className="text-xs font-medium text-slate-500">
                          {m.student_id || "(Unknown)"}
                        </span>
                        <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md ${m.status === 'approved' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : m.status === 'rejected' ? 'bg-rose-50 text-rose-700 border border-rose-100' : 'bg-amber-50 text-amber-700 border border-amber-100'}`}>
                          {m.status}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        id={`dashboard-approve-${m.id}`}
                        onClick={() => updateMemberStatus(m.id, true)}
                        className="rounded-xl bg-emerald-600 hover:bg-emerald-700 px-4 py-2 text-xs font-bold text-white transition disabled:opacity-40 shadow-sm"
                        disabled={m.status === "approved"}
                      >
                        Approve
                      </button>
                      <button
                        id={`dashboard-reject-${m.id}`}
                        onClick={() => updateMemberStatus(m.id, false)}
                        className="rounded-xl bg-rose-600 hover:bg-rose-700 px-4 py-2 text-xs font-bold text-white transition disabled:opacity-40 shadow-sm"
                        disabled={m.status === "rejected"}
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {!loading && selectedClassId && filteredMembers.length === 0 ? (
                <p className="text-sm font-medium text-slate-500 bg-slate-50 p-6 rounded-2xl text-center border border-dashed border-slate-300">No students match filter.</p>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </MainLayout>
  );
}
