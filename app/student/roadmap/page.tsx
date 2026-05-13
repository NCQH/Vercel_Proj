"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import MainLayout from "../../../components/app-shell/MainLayout";
import { apiClient, type RoadmapItem, type RoadmapStatus } from "../../../lib/api-client";
import { useToast } from "../../../components/ui/ToastProvider";


export default function StudentRoadmapPage() {
  const { data: session, status } = useSession();
  const [items, setItems] = useState<RoadmapItem[]>([]);
  const [nextAction, setNextAction] = useState<RoadmapItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updatingItemId, setUpdatingItemId] = useState("");
  const [error, setError] = useState("");
  const { showToast } = useToast();

  const identity =
    (session?.user as { id?: string } | undefined)?.id ||
    session?.user?.email ||
    session?.user?.name ||
    "";

  const loadRoadmap = async () => {
    if (!identity) return;
    setLoading(true);
    setError("");
    try {
      const data = await apiClient.roadmap.get();
      setItems(data.items || []);
      setNextAction(data.next_action || null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load roadmap.";
      setError(message);
      showToast({ type: "error", title: "Roadmap load failed", message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (status !== "authenticated") return;
    loadRoadmap();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, identity]);

  const refreshRoadmap = async () => {
    if (!identity || refreshing) return;
    setRefreshing(true);
    setError("");
    try {
      const data = await apiClient.roadmap.refresh();
      setItems(data.items || []);
      setNextAction(data.next_action || null);
      showToast({ type: "success", title: "Roadmap refreshed", message: "Your learning plan is up to date." });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to refresh roadmap.";
      setError(message);
      showToast({ type: "error", title: "Refresh failed", message });
    } finally {
      setRefreshing(false);
    }
  };

  const updateItem = async (item: RoadmapItem, nextStatus: RoadmapStatus) => {
    if (!identity || updatingItemId) return;
    const nextProgress = nextStatus === "done" ? 100 : nextStatus === "doing" ? Math.max(item.progress, 40) : Math.min(item.progress, 20);
    setUpdatingItemId(item.id);
    setError("");
    try {
      await apiClient.roadmap.updateItem(item.id, { status: nextStatus, progress: nextProgress });
      await loadRoadmap();
      showToast({ type: "success", title: "Progress updated", message: `${item.topic} marked as ${nextStatus}.` });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update roadmap item.";
      setError(message);
      showToast({ type: "error", title: "Update failed", message });
    } finally {
      setUpdatingItemId("");
    }
  };

  const grouped = {
    high: items.filter((i) => i.priority === "high"),
    medium: items.filter((i) => i.priority === "medium"),
    low: items.filter((i) => i.priority === "low"),
  };

  if (loading) {
    return <MainLayout role="student"><div className="p-8">Loading roadmap...</div></MainLayout>;
  }

  return (
    <MainLayout role="student">
      <section className="mx-auto w-full max-w-7xl space-y-6">
        <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-soft">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-brand-600">Study roadmap</p>
              <h1 className="mt-3 text-3xl font-semibold text-slate-950">Your personal learning plan</h1>
              <p className="mt-2 text-slate-600">AI-generated adaptive plan from your study behavior and available materials.</p>
            </div>
            <div className="flex gap-2">
              <button id="roadmap-refresh" onClick={refreshRoadmap} disabled={refreshing} className="rounded-xl bg-emerald-600 px-3 py-2 text-sm text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60">{refreshing ? "Refreshing..." : "Refresh"}</button>
            </div>
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-900 shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-bold">Roadmap needs attention</p>
                <p className="mt-1 text-xs font-medium opacity-80">{error}</p>
              </div>
              <button type="button" onClick={loadRoadmap} className="rounded-xl bg-rose-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-rose-700">
                Retry
              </button>
            </div>
          </div>
        ) : null}

        {nextAction ? (
          <div className="rounded-[24px] bg-[#1E1B4B] text-white p-8 relative overflow-hidden shadow-[0_4px_20px_rgba(30,27,75,0.2)]">
            <div className="absolute -top-10 -right-10 p-8 opacity-5">
               <span className="text-[200px]">🎯</span>
            </div>
            <div className="relative z-10">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-indigo-300">🎯 Recommended Next Lesson</p>
              <h2 className="mt-3 text-3xl font-bold text-white">{nextAction.topic}</h2>
              <div className="mt-4 max-w-2xl bg-white/5 rounded-xl p-4 border border-white/10 backdrop-blur-sm">
                <p className="text-xs font-bold text-indigo-200 uppercase tracking-wider mb-2">Why this matters</p>
                <p className="text-indigo-50 leading-relaxed text-sm">{nextAction.description}</p>
              </div>
              <div className="mt-6 flex flex-wrap items-center gap-4">
                 <button onClick={() => updateItem(nextAction, "doing")} disabled={Boolean(updatingItemId)} className="px-6 py-2.5 bg-white text-indigo-950 font-bold rounded-full text-sm hover:bg-indigo-50 transition shadow-sm disabled:cursor-not-allowed disabled:opacity-60">▶ Start Lesson</button>
                 <span className="px-4 py-2 bg-white/10 rounded-full text-xs font-semibold backdrop-blur text-indigo-100">Estimated: {nextAction.eta_minutes} min</span>
              </div>
            </div>
          </div>
        ) : null}

        <div className="mt-10 space-y-2">
          <h2 className="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">📍 Learning Path</h2>
          {items.map((item, index) => (
            <div key={item.id} className="relative pl-10 pb-6">
              <div className="absolute left-4 top-8 bottom-0 w-[2px] bg-slate-200"></div>
              <div className={`absolute left-0 top-1 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-4 border-white ${item.status === 'done' ? 'bg-emerald-500 text-white' : item.status === 'doing' ? 'bg-brand-500 text-white' : 'bg-slate-200 text-slate-600'}`}>
                {index + 1}
              </div>
              <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)] hover:shadow-md transition">
                 <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="flex-1">
                      <h4 className="font-bold text-slate-900 text-lg">{item.topic}</h4>
                      <p className="mt-1 text-sm text-slate-600 leading-relaxed">{item.description}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 shrink-0">
                      {item.status !== 'done' && (
                        <button id={`item-doing-${item.id}`} onClick={() => updateItem(item, "doing")} disabled={Boolean(updatingItemId)} className="rounded-xl border border-slate-300 bg-white hover:bg-slate-50 px-4 py-2 text-xs font-bold text-slate-700 transition disabled:cursor-not-allowed disabled:opacity-60">{updatingItemId === item.id ? "Updating..." : "▶ Start"}</button>
                      )}
                      {item.status !== 'done' && (
                        <button id={`item-done-${item.id}`} onClick={() => updateItem(item, "done")} disabled={Boolean(updatingItemId)} className="rounded-xl bg-emerald-600 hover:bg-emerald-700 px-4 py-2 text-xs font-bold text-white transition shadow-sm disabled:cursor-not-allowed disabled:opacity-60">{updatingItemId === item.id ? "Updating..." : "✓ Complete"}</button>
                      )}
                      {item.status === 'done' && (
                        <button id={`item-reset-${item.id}`} onClick={() => updateItem(item, "todo")} disabled={Boolean(updatingItemId)} className="rounded-xl border border-slate-300 bg-white hover:bg-slate-50 px-4 py-2 text-xs font-bold text-slate-700 transition disabled:cursor-not-allowed disabled:opacity-60">{updatingItemId === item.id ? "Updating..." : "↺ Review Again"}</button>
                      )}
                    </div>
                 </div>
                 
                 <div className="mt-4 flex flex-wrap items-center gap-3 text-xs font-semibold text-slate-600">
                    <span className="flex items-center gap-1.5 px-2.5 py-1.5 bg-slate-100 rounded-lg">⏱ {item.eta_minutes} min</span>
                    <span className={`px-2.5 py-1.5 rounded-lg ${item.priority === 'high' ? 'bg-rose-50 text-rose-700' : item.priority === 'medium' ? 'bg-amber-50 text-amber-700' : 'bg-slate-100 text-slate-700'} capitalize`}>Priority: {item.priority}</span>
                    <span className={`px-2.5 py-1.5 rounded-lg ${item.status === 'done' ? 'bg-emerald-50 text-emerald-700' : item.status === 'doing' ? 'bg-brand-50 text-brand-700' : 'bg-slate-100'}`}>Status: {item.status}</span>
                 </div>
                 
                 {item.actions.length > 0 && (
                   <div className="mt-5 pl-5 border-l-2 border-slate-100">
                     <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Tasks</p>
                     <ul className="space-y-2 text-sm text-slate-700">
                        {item.actions.map((a) => <li key={a} className="flex gap-3">
                           <span className="text-slate-300 mt-0.5">├─</span> 
                           <span>{a}</span>
                        </li>)}
                     </ul>
                   </div>
                 )}
                 
                 <div className="mt-5">
                    <div className="flex justify-between text-[11px] uppercase tracking-wider font-bold text-brand-600 mb-1.5">
                       <span>Progress</span>
                       <span>{item.progress}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                       <div className="h-full rounded-full bg-brand-600 transition-all duration-500" style={{ width: `${item.progress}%` }} />
                    </div>
                 </div>
              </article>
            </div>
          ))}
          {items.length === 0 ? <p className="text-sm text-slate-500">No roadmap items available.</p> : null}
        </div>
      </section>
    </MainLayout>
  );
}
