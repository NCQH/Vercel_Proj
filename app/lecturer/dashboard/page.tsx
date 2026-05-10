"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import MainLayout from "../../../components/app-shell/MainLayout";

type ClassItem = { id: string; name: string; code: string; description?: string };
type MemberItem = {
  id: string;
  class_id: string;
  student_id: string;
  full_name?: string;
  student_name?: string;
  student_email?: string;
  status: "pending" | "approved" | "rejected";
  requested_at?: string;
  approved_at?: string;
};

export default function LecturerDashboardPage() {
  const { data: session, status } = useSession();
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [selectedClassId, setSelectedClassId] = useState("");
  const [members, setMembers] = useState<MemberItem[]>([]);
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
    const res = await fetch(`/api/classes?user_id=${encodeURIComponent(identity)}&role=lecturer`, {
      cache: "no-store",
    });
    const data = await res.json();
    if (!res.ok) {
      setError(data?.detail || "Failed to load classes");
      return;
    }

    const items = (data.items || []) as ClassItem[];
    setClasses(items);
    if (!selectedClassId && items[0]?.id) setSelectedClassId(items[0].id);
  };

  const loadMembers = async (classId: string) => {
    if (!identity || !classId) return;
    setLoading(true);
    setError("");
    const res = await fetch(
      `/api/classes/members?user_id=${encodeURIComponent(identity)}&class_id=${encodeURIComponent(classId)}`,
      { cache: "no-store" }
    );
    const data = await res.json();
    if (!res.ok) {
      setMembers([]);
      setError(data?.detail || "Failed to load students");
      setLoading(false);
      return;
    }
    setMembers((data.items || []) as MemberItem[]);
    setLoading(false);
  };

  const updateMemberStatus = async (membershipId: string, approve: boolean) => {
    if (!identity) return;
    setError("");
    const fd = new FormData();
    fd.append("user_id", identity);
    fd.append("approve", String(approve));

    const res = await fetch(`/api/classes/members/${membershipId}/approve`, {
      method: "POST",
      body: fd,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data?.detail || "Failed to update student status");
      return;
    }

    await loadMembers(selectedClassId);
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

  return (
    <MainLayout role="lecturer">
      <section className="mx-auto w-full max-w-6xl space-y-6">
        <div className="rounded-[24px] border border-slate-200 bg-white p-8 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
          <p className="text-xs uppercase tracking-[0.2em] font-bold text-brand-600">Lecturer dashboard</p>
          <h1 className="mt-2 text-3xl font-bold text-slate-900">Manage your class students</h1>
          <p className="mt-2 text-sm text-slate-600">Choose a class, review student memberships, and approve or reject quickly.</p>
          {error ? <p className="mt-3 text-sm font-semibold text-rose-600 bg-rose-50 px-3 py-2 rounded-xl border border-rose-100 inline-block">{error}</p> : null}
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
                   <span className="text-amber-600 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-100">Pending: {countBy("pending")}</span>
                   <span className="text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-100">Approved: {countBy("approved")}</span>
                   <span className="text-rose-600 bg-rose-50 px-2.5 py-1 rounded-md border border-rose-100">Rejected: {countBy("rejected")}</span>
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
