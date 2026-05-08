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
        <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft">
          <p className="text-sm uppercase tracking-[0.24em] text-brand-600">Lecturer dashboard</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-950">Manage your class students</h1>
          <p className="mt-3 text-slate-600">Choose class, review student memberships, approve or reject quickly.</p>
          {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
        </div>

        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <aside className="rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-slate-900">Your classes</h2>
            <div className="mt-4 space-y-2">
              {classes.map((c) => (
                <button
                  key={c.id}
                  id={`dashboard-class-${c.id}`}
                  onClick={() => setSelectedClassId(c.id)}
                  className={`w-full rounded-xl border px-3 py-2 text-left transition ${selectedClassId === c.id
                    ? "border-brand-500 bg-brand-50"
                    : "border-slate-200 hover:border-brand-300"
                    }`}
                >
                  <div className="font-medium text-slate-900">{c.name}</div>
                  <div className="text-xs text-slate-500">Code: {c.code}</div>
                </button>
              ))}
              {classes.length === 0 ? <p className="text-sm text-slate-500">No class created yet.</p> : null}
            </div>
          </aside>

          <div className="rounded-3xl border border-slate-200 bg-white p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {selectedClass ? `Students in ${selectedClass.name}` : "Select class to manage students"}
                </h2>
                <p className="mt-1 text-sm text-slate-600">Pending: {countBy("pending")} · Approved: {countBy("approved")} · Rejected: {countBy("rejected")}</p>
              </div>
              <select
                id="member-status-filter"
                value={filter}
                onChange={(e) => setFilter(e.target.value as "all" | "pending" | "approved" | "rejected")}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
              >
                <option value="all">All statuses</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>

            <div className="mt-5 space-y-3">
              {loading ? <p className="text-sm text-slate-500">Loading students...</p> : null}

              {!loading && filteredMembers.map((m) => (
                <div key={m.id} className="rounded-2xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <div className="font-medium text-slate-900">
                        {m.full_name || m.student_name || "(Unknown)"}
                      </div>
                      <div className="text-xs text-slate-500">
                        {m.student_id || "(Unknown)"}
                      </div>
                      <div className="text-xs text-slate-500">Status: {m.status}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        id={`dashboard-approve-${m.id}`}
                        onClick={() => updateMemberStatus(m.id, true)}
                        className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
                        disabled={m.status === "approved"}
                      >
                        Approve
                      </button>
                      <button
                        id={`dashboard-reject-${m.id}`}
                        onClick={() => updateMemberStatus(m.id, false)}
                        className="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-40"
                        disabled={m.status === "rejected"}
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </div>
              ))}

              {!loading && selectedClassId && filteredMembers.length === 0 ? (
                <p className="text-sm text-slate-500">No students match filter.</p>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </MainLayout>
  );
}
