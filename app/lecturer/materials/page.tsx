import MainLayout from "../../../components/app-shell/MainLayout";

export default function LecturerMaterialsPage() {
  return (
    <MainLayout role="lecturer">
      <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft">
        <div className="mb-6">
          <p className="text-sm uppercase tracking-[0.24em] text-brand-600">
            Material management
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-950">
            Upload and index content
          </h1>
          <p className="mt-3 text-slate-600">
            A drag-and-drop upload zone and indexed material list will be
            available here for course asset management.
          </p>
        </div>
        <div className="rounded-3xl bg-slate-50 p-6 text-slate-700">
          <p className="font-medium">
            Upload supported files like PDFs, PPTXs, and video transcripts for
            AI indexing.
          </p>
        </div>
      </div>
    </MainLayout>
  );
}
