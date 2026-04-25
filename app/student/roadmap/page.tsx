import MainLayout from "../../../components/app-shell/MainLayout";

export default function StudentRoadmapPage() {
  return (
    <MainLayout role="student">
      <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft">
        <div className="mb-6">
          <p className="text-sm uppercase tracking-[0.24em] text-brand-600">
            Study roadmap
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-950">
            Your review plan
          </h1>
          <p className="mt-3 text-slate-600">
            A dedicated page for your personalized revision topics, next
            practice checkpoints, and knowledge gap trends.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-3xl bg-brand-50 p-6">
            <h2 className="text-xl font-semibold text-slate-950">
              Next checkpoint
            </h2>
            <p className="mt-3 text-slate-600">
              Review formative assessment strategies before the next tutoring
              session.
            </p>
          </div>
          <div className="rounded-3xl bg-slate-100 p-6">
            <h2 className="text-xl font-semibold text-slate-950">
              Suggested citations
            </h2>
            <ul className="mt-4 space-y-3 text-sm text-slate-700">
              <li className="rounded-2xl bg-white p-4 shadow-sm">
                Slide 12: Assessment framework
              </li>
              <li className="rounded-2xl bg-white p-4 shadow-sm">
                Lecture 03: GDP and inflation
              </li>
              <li className="rounded-2xl bg-white p-4 shadow-sm">
                Transcript section: case study review
              </li>
            </ul>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
