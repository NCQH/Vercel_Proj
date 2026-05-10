"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

export default function SignupPage() {
  const { status } = useSession();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("student");
  const [saving, setSaving] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    } else if (status === "authenticated") {
      fetch("/api/users/me")
        .then((res) => res.json())
        .then((data) => {
          if (data?.onboarded) {
            const role = String(data?.profile?.class_name || "student").toLowerCase();
            router.replace(role === "lecturer" ? "/lecturer/dashboard" : "/student/chat");
          } else {
            setIsChecking(false);
          }
        })
        .catch((err) => {
          console.error(err);
          setIsChecking(false);
        });
    }
  }, [status, router]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!fullName.trim() || !role) {
      setError("Please enter full name and select a role.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch("/api/users/onboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName.trim(),
          role: role,
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || "Could not save profile");
      }

      router.replace(role === "lecturer" ? "/lecturer/dashboard" : "/student/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  };

  if (status === "loading" || (status === "authenticated" && isChecking)) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-900">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
          <p className="text-sm font-semibold text-slate-600">Checking profile status...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900 flex items-center justify-center">
      <section className="mx-auto w-full max-w-xl rounded-[24px] border border-slate-200 bg-white p-8 shadow-[0_4px_20px_rgba(15,23,42,0.04)] sm:p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(99,102,241,0.08),_transparent_50%)] pointer-events-none" />
        <div className="relative z-10">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600 mb-6">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
          </div>
          <h1 className="text-3xl font-bold text-slate-900">Complete your profile</h1>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            Tell us a bit about yourself so the AI Assistant can personalize your learning context perfectly.
          </p>

          <form id="signup-form" onSubmit={handleSubmit} className="mt-8 space-y-5">
            <label htmlFor="full-name-input" className="block space-y-2">
              <span className="text-sm font-bold text-slate-900">Full name</span>
              <input
                id="full-name-input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-brand-500 focus:bg-white focus:ring-1 focus:ring-brand-500"
                placeholder="e.g. Nguyen Van A"
              />
            </label>

            <label htmlFor="role-select" className="block space-y-2">
              <span className="text-sm font-bold text-slate-900">Select your role</span>
              <select
                id="role-select"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium outline-none transition focus:border-brand-500 focus:bg-white focus:ring-1 focus:ring-brand-500 cursor-pointer text-slate-700"
              >
                <option value="student">👨‍🎓 Student</option>
                <option value="lecturer">👨‍🏫 Lecturer</option>
              </select>
            </label>

            {error ? (
              <p id="signup-error" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700 shadow-sm">
                {error}
              </p>
            ) : null}

            <button
              id="signup-submit-btn"
              type="submit"
              disabled={saving}
              className="mt-4 w-full rounded-xl bg-brand-600 px-5 py-3.5 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60 shadow-sm"
            >
              {saving ? "Saving profile..." : "Finish Sign up"}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
