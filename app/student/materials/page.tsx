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
    if (!code || !identity) return;
    setError("");
    const fd = new FormData();
    fd.append("user_id", identity);
    fd.append("class_code", code);
    const res = await fetch("/api/classes/join", { method: "POST", body: fd });
    if (!res.ok) {
      setError("Join request failed");
      return;
    }
    const membershipItems = await loadMemberships();
    await loadApprovedClassFiles(membershipItems);
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
                return (
                <div key={c.id} className="rounded-xl border border-slate-200 px-3 py-2">
                  <div className="font-medium text-slate-900">{c.name}</div>
                  {!isApproved ? (
                    <button id={`request-join-${c.id}`} onClick={() => requestJoin(c.code)} className="mt-2 rounded-lg bg-slate-900 px-3 py-1 text-xs text-white">Request Join</button>
                  ) : null}
                </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-slate-900">My Memberships</h2>
            <div className="mt-3 space-y-2">
              {memberships.map((m) => (
                <button key={m.membership_id} id={`membership-${m.membership_id}`} onClick={() => m.class?.id && setSelectedClassId(m.class.id)} className="w-full rounded-xl border border-slate-200 px-3 py-2 text-left">
                  <div className="font-medium text-slate-900">{m.class?.name || "Unknown class"}</div>
                  <div className="text-xs text-slate-600">Status: {m.status}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6">
          <h2 className="text-xl font-semibold text-slate-900">Approved Class Files</h2>
          <div className="mt-3 space-y-2">
            {classFiles.map((f) => (
              <div key={`${f.class_id || "no-class"}-${f.file_id}`} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2">
                <div>
                  <div>{f.original_filename}</div>
                  <div className="text-xs text-slate-500">Class: {f.class_name || "Unknown class"}</div>
                </div>
                <a id={`download-class-file-${f.file_id}`} href={`/api/class-files/download?user_id=${encodeURIComponent(identity)}&file_id=${encodeURIComponent(f.file_id)}`} className="text-brand-700">Download</a>
              </div>
            ))}
            {classFiles.length === 0 ? <p className="text-sm text-slate-500">No accessible class files yet.</p> : null}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-6">
          <h2 className="text-xl font-semibold text-slate-900">My Uploaded Files</h2>
          <div className="mt-3 space-y-2">
            {personalUploads.map((f) => (
              <div key={f.file_id} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2">
                <span>{f.filename}</span>
                <a id={`download-personal-file-${f.file_id}`} href={`/api/uploads/download?user_id=${encodeURIComponent(identity)}&file_id=${encodeURIComponent(f.file_id)}`} className="text-brand-700">Download</a>
              </div>
            ))}
            {personalUploads.length === 0 ? <p className="text-sm text-slate-500">No personal uploaded files yet.</p> : null}
          </div>
        </div>
      </section>
    </MainLayout>
  );
}
