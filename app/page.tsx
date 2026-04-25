import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-200 bg-white p-10 shadow-soft">
        <div className="space-y-6 text-center">
          <div className="inline-flex items-center justify-center rounded-2xl bg-brand-100 px-4 py-2 text-brand-700">
            AI Teaching Assistant
          </div>
          <h1 className="text-4xl font-semibold tracking-tight text-slate-900">
            Launch the classroom experience
          </h1>
          <p className="mx-auto max-w-2xl text-lg leading-8 text-slate-600">
            Choose your role to explore the student learning assistant or
            lecturer course manager with analytics and review workflows.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <Link
              href="/login"
              className="rounded-2xl bg-brand-600 px-6 py-4 text-white shadow-soft transition hover:bg-brand-700"
            >
              Go to Login
            </Link>
            <Link
              href="/student/chat"
              className="rounded-2xl border border-slate-200 px-6 py-4 text-slate-700 transition hover:bg-slate-50"
            >
              Preview Student UI
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
