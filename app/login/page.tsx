"use client";

import { signIn } from "next-auth/react";
import { Sparkles, ShieldCheck, GraduationCap } from "lucide-react";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
      <section className="mx-auto grid w-full max-w-5xl overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-soft lg:grid-cols-[1.1fr_0.9fr]">
        <div className="relative p-8 sm:p-12">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(99,102,241,0.12),_transparent_58%)]" />
          <div className="relative space-y-6">
            <p className="inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-indigo-700">
              <Sparkles className="h-3.5 w-3.5" />
              AI Teaching Assistant
            </p>
            <h1 className="text-4xl font-semibold leading-tight text-slate-900 sm:text-5xl">
              Welcome back to your learning cockpit
            </h1>
            <p className="max-w-xl text-base leading-7 text-slate-600">
              Sign in to continue your personalized learning journey or create a
              new student profile with class information for smarter context.
            </p>
            <div className="grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <ShieldCheck className="mb-2 h-4 w-4 text-emerald-600" />
                Secure Google authentication
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <GraduationCap className="mb-2 h-4 w-4 text-indigo-600" />
                Profile-based tutoring memory
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col justify-center gap-4 border-t border-slate-200 bg-slate-50 p-8 sm:p-10 lg:border-l lg:border-t-0">
          <h2 className="text-2xl font-semibold text-slate-900">Get Started</h2>
          <p className="text-sm leading-6 text-slate-600">
            Choose login if you already completed profile setup. Choose sign up
            if this is your first time.
          </p>

          <button
            id="login-google-btn"
            type="button"
            onClick={() => signIn("google", { callbackUrl: "/student/chat" })}
            className="inline-flex items-center justify-center gap-2 rounded-2xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700"
          >
            Login with Google
          </button>

          <button
            id="signup-google-btn"
            type="button"
            onClick={() => signIn("google", { callbackUrl: "/signup" })}
            className="inline-flex items-center justify-center gap-2 rounded-2xl border border-indigo-200 bg-white px-5 py-3 text-sm font-semibold text-indigo-700 transition hover:bg-indigo-50"
          >
            Sign up with Google
          </button>
        </div>
      </section>
    </main>
  );
}
