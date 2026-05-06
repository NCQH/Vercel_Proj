"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import MainLayout from "../../../components/app-shell/MainLayout";

type RoadmapItem = {
  id: string;
  topic: string;
  description: string;
  priority: "high" | "medium" | "low";
  eta_minutes: number;
  progress: number;
  status: "todo" | "doing" | "done";
  sources: string[];
  actions: string[];
};

export default function StudentRoadmapPage() {
  const { data: session, status } = useSession();
  const [items, setItems] = useState<RoadmapItem[]>([]);
  const [nextAction, setNextAction] = useState<RoadmapItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const identity =
    (session?.user as { id?: string } | undefined)?.id ||
    session?.user?.email ||
    session?.user?.name ||
    "";

  const loadRoadmap = async () => {
    if (!identity) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/roadmap?user_id=${encodeURIComponent(identity)}`, { cache: "no-store" });
      const data = await res.json();
      setItems(data.items || []);
      setNextAction(data.next_action || null);
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
    if (!identity) return;
    setRefreshing(true);
    try {
      const res = await fetch("/api/roadmap/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: identity }),
      });
      const data = await res.json();
      setItems(data.items || []);
      setNextAction(data.next_action || null);
    } finally {
      setRefreshing(false);
    }
  };

  const updateItem = async (item: RoadmapItem, nextStatus: "todo" | "doing" | "done") => {
    if (!identity) return;
    const nextProgress = nextStatus === "done" ? 100 : nextStatus === "doing" ? Math.max(item.progress, 40) : Math.min(item.progress, 20);
    await fetch(`/api/roadmap/items/${encodeURIComponent(item.id)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: identity, status: nextStatus, progress: nextProgress }),
    });
    await loadRoadmap();
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
              <button id="roadmap-refresh" onClick={refreshRoadmap} className="rounded-xl bg-emerald-600 px-3 py-2 text-sm text-white">{refreshing ? "Refreshing..." : "Refresh"}</button>
            </div>
          </div>
        </div>

        {nextAction ? (
          <div className="rounded-3xl border border-brand-200 bg-brand-50 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">Next best action</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">{nextAction.topic}</h2>
            <p className="mt-2 text-slate-700">{nextAction.description}</p>
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-3">
          {(["high", "medium", "low"] as const).map((prio) => (
            <div key={prio} className="rounded-3xl border border-slate-200 bg-white p-5">
              <h3 className="text-lg font-semibold capitalize text-slate-900">{prio} priority</h3>
              <div className="mt-4 space-y-4">
                {grouped[prio].map((item) => (
                  <article key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <h4 className="font-semibold text-slate-900">{item.topic}</h4>
                    <p className="mt-1 text-sm text-slate-600">{item.description}</p>
                    <p className="mt-2 text-xs text-slate-500">ETA: {item.eta_minutes}m • Progress: {item.progress}% • Status: {item.status}</p>
                    <div className="mt-2 h-2 rounded-full bg-slate-200"><div className="h-full rounded-full bg-brand-600" style={{ width: `${item.progress}%` }} /></div>
                    <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-slate-700">
                      {item.actions.map((a) => <li key={a}>{a}</li>)}
                    </ul>
                    <p className="mt-2 text-xs text-slate-500">Sources: {item.sources.join(", ") || "None"}</p>
                    <div className="mt-3 flex gap-2">
                      <button id={`item-doing-${item.id}`} onClick={() => updateItem(item, "doing")} className="rounded-lg border border-slate-300 px-2 py-1 text-xs">Doing</button>
                      <button id={`item-done-${item.id}`} onClick={() => updateItem(item, "done")} className="rounded-lg bg-emerald-600 px-2 py-1 text-xs text-white">Done</button>
                      <button id={`item-reset-${item.id}`} onClick={() => updateItem(item, "todo")} className="rounded-lg border border-slate-300 px-2 py-1 text-xs">Reset</button>
                    </div>
                  </article>
                ))}
                {grouped[prio].length === 0 ? <p className="text-sm text-slate-500">No items.</p> : null}
              </div>
            </div>
          ))}
        </div>
      </section>
    </MainLayout>
  );
}
