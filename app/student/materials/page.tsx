"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import MainLayout from "../../../components/app-shell/MainLayout";

type UploadItem = {
  file_id: string;
  filename: string;
  path: string;
  size: number;
  uploaded_at: string;
};

export default function StudentMaterialsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [items, setItems] = useState<UploadItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [error, setError] = useState("");

  const identity =
    (session?.user as { id?: string } | undefined)?.id ||
    session?.user?.email ||
    session?.user?.name ||
    "";

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  const loadItems = async () => {
    if (!identity) {
      setIsLoading(false);
      setError("You need to sign in to view materials.");
      return;
    }
    try {
      const response = await fetch(`/api/uploads?user_id=${encodeURIComponent(identity)}`, {
        cache: "no-store",
      });
      if (!response.ok) throw new Error("Failed to load material list");
      const payload = await response.json();
      setItems(payload.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const bootstrap = async () => {
      if (status !== "authenticated") return;
      setIsBootstrapping(true);
      try {
        await loadItems();
      } finally {
        setIsBootstrapping(false);
      }
    };

    bootstrap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, identity]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || isUploading) return;

    if (!identity) {
      setError("You need to sign in before uploading files.");
      if (event.target) event.target.value = "";
      return;
    }

    setIsUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("user_id", identity);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");
      await loadItems();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsUploading(false);
      if (event.target) event.target.value = "";
    }
  };

  if (status === "loading" || isBootstrapping) {
    return (
      <MainLayout role="student">
        <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
          <p className="text-sm font-medium text-slate-600">Loading backend data...</p>
        </div>
      </MainLayout>
    );
  }

  if (status === "unauthenticated") {
    return (
      <MainLayout role="student">
        <div className="flex min-h-[70vh] flex-col items-center justify-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
          <p className="text-sm font-medium text-slate-600">Redirecting to login...</p>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout role="student">
      <section className="mx-auto w-full max-w-5xl space-y-6">
        <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-brand-600">Materials</p>
              <h1 className="mt-2 text-3xl font-semibold text-slate-900">Learning Materials Management</h1>
              <p className="mt-2 text-sm text-slate-600">Upload files and view the material list for each user account.</p>
            </div>
            <button
              id="upload-material-btn"
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="rounded-2xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {isUploading ? "Uploading..." : "Upload Material"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.txt,.md,.doc,.docx"
              onChange={handleUpload}
            />
          </div>
        </div>

        <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft">
          <h2 className="text-xl font-semibold text-slate-900">Uploaded Files</h2>

          {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

          {isLoading ? (
            <p className="mt-4 text-sm text-slate-600">Loading data...</p>
          ) : items.length === 0 ? (
            <p className="mt-4 text-sm text-slate-600">No materials uploaded yet.</p>
          ) : (
            <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-sm">
                <thead className="bg-slate-50 text-left text-slate-600">
                  <tr>
                    <th className="px-4 py-3 font-medium">Filename</th>
                    <th className="px-4 py-3 font-medium">Size</th>
                    <th className="px-4 py-3 font-medium">Uploaded At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {items.map((item) => (
                    <tr key={item.file_id}>
                      <td className="px-4 py-3 text-slate-900">{item.filename}</td>
                      <td className="px-4 py-3 text-slate-600">{Math.round(item.size / 1024)} KB</td>
                      <td className="px-4 py-3 text-slate-600">{item.uploaded_at || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </MainLayout>
  );
}
