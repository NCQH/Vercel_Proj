"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

export default function SignupPage() {
  const { status } = useSession();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [className, setClassName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    if (!fullName.trim() || !className.trim()) {
      setError("Please enter both full name and class.");
      return;
    }

    setSaving(true);
    try {
      const response = await fetch("/api/users/onboard", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName.trim(),
          class_name: className.trim(),
        }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || "Could not save profile");
      }

      router.replace("/student/chat");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSaving(false);
    }
  };

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        Loading session...
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

          <label htmlFor="class-name-input" className="block space-y-2">
            <span className="text-sm text-slate-200">Class</span>
            <input
              id="class-name-input"
              value={className}
              onChange={(e) => setClassName(e.target.value)}
              className="w-full rounded-2xl border border-white/20 bg-white/5 px-4 py-3 text-sm outline-none transition focus:border-indigo-300"
              placeholder="SE-AI-2026"
            />
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
