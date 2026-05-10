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
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(99,102,241,0.15),_transparent_70%)] pointer-events-none" />
      <section className="relative mx-auto flex w-full max-w-3xl flex-col items-center gap-6 rounded-[32px] border border-white bg-white/80 p-10 text-center shadow-[0_8px_40px_rgba(15,23,42,0.08)] backdrop-blur-xl sm:p-16">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-[24px] bg-brand-600 text-white shadow-lg mb-2">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        </div>
        <p className="rounded-full border border-brand-200 bg-brand-50 px-5 py-2.5 text-[11px] font-bold uppercase tracking-[0.2em] text-brand-700">
          AI Teaching Assistant
        </p>

        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-6xl leading-[1.15]">
          Your Personalized <br className="hidden sm:block"/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-indigo-500">Learning Companion</span>
        </h1>

        <p className="max-w-xl text-base leading-relaxed text-slate-600 font-medium sm:text-lg mt-2">
          Chat with an intelligent tutor, extract insights from your syllabus, and master concepts faster with tailored roadmaps.
        </p>

        <div className="mt-6 flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
          <Link
            id="start-btn"
            href="/login"
            className="w-full sm:w-auto rounded-2xl bg-slate-900 px-8 py-4 text-sm font-bold text-white transition hover:bg-slate-800 shadow-[0_4px_14px_0_rgb(0,0,0,0.39)] hover:shadow-[0_6px_20px_rgba(0,0,0,0.23)] hover:-translate-y-0.5 flex items-center justify-center gap-2"
          >
            <span>Get Started</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
          </Link>
        </div>
      </section>
    </main>
  );
}
