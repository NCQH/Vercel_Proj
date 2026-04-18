import MainLayout from "../../../components/app-shell/MainLayout";

export default function LecturerDashboardPage() {
  return (
    <MainLayout role="lecturer">
      <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft">
        <div className="mb-6">
          <p className="text-sm uppercase tracking-[0.24em] text-brand-600">
            Lecturer dashboard
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-950">
            Class insights
          </h1>
          <p className="mt-3 text-slate-600">
            Analytics and material controls will appear here once the instructor
            workflow is ready.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
            <h2 className="text-xl font-semibold text-slate-950">
              KPI snapshot
            </h2>
            <p className="mt-3 text-slate-600">
              Total queries, times saved, and knowledge gap trends in a clean
              layout.
            </p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-6">
            <h2 className="text-xl font-semibold text-slate-950">
              Material uploads
            </h2>
            <p className="mt-3 text-slate-600">
              Easily index PDFs, slides, and transcripts for AI-assisted class
              support.
            </p>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
