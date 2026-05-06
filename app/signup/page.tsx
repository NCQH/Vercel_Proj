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
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-700 border-t-indigo-500" />
          <p>Checking profile status...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-white">
      <section className="mx-auto w-full max-w-xl rounded-[2rem] border border-white/10 bg-gradient-to-b from-slate-900 to-slate-950 p-8 shadow-2xl sm:p-10">
        <h1 className="text-3xl font-semibold">Complete your sign up</h1>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Enter your profile details so the assistant can personalize learning context.
        </p>

        <form id="signup-form" onSubmit={handleSubmit} className="mt-8 space-y-5">
          <label htmlFor="full-name-input" className="block space-y-2">
            <span className="text-sm text-slate-200">Full name</span>
            <input
              id="full-name-input"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-2xl border border-white/20 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-indigo-300"
              placeholder="Nguyen Van A"
            />
          </label>

          <label htmlFor="role-select" className="block space-y-2">
            <span className="text-sm text-slate-200">Role</span>
            <select
              id="role-select"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-2xl border border-white/20 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-indigo-300"
            >
              <option value="student" className="bg-slate-900 text-white">Student</option>
              <option value="lecturer" className="bg-slate-900 text-white">Lecturer</option>
            </select>
          </label>

          {error ? (
            <p id="signup-error" className="rounded-xl border border-red-300/40 bg-red-400/10 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          <button
            id="signup-submit-btn"
            type="submit"
            disabled={saving}
            className="w-full rounded-2xl bg-indigo-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Saving profile..." : "Finish Sign up"}
          </button>
        </form>
      </section>
    </main>
  );
}
