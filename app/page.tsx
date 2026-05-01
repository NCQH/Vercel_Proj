"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

export default function HomePage() {
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/student/chat");
    }
  }, [status, router]);

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
          <p className="text-sm font-medium text-slate-600">Checking session...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10">
      <section className="mx-auto flex w-full max-w-3xl flex-col items-center gap-6 rounded-[2rem] border border-slate-200 bg-white p-10 text-center shadow-soft sm:p-14">
        <p className="rounded-full border border-brand-200 bg-brand-50 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-brand-700">
          AI Teaching Assistant
        </p>

        <h1 className="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
          Your Personalized AI Learning Assistant
        </h1>

        <p className="max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
          Chat with AI, learn from your own documents, and get support tailored to your study context.
        </p>

        <Link
          id="start-btn"
          href="/login"
          className="mt-2 rounded-2xl bg-brand-600 px-8 py-3 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          Start
        </Link>
      </section>
    </main>
  );
}
