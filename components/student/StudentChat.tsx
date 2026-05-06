"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Paperclip, Send } from "lucide-react";
import ChatBubble from "../ui/ChatBubble";
import MainLayout from "../app-shell/MainLayout";

type Message = {
  id: string;
  role: string;
  text: string;
  citations?: any[];
};

type UserProfile = {
  full_name: string;
  class_name: string;
  email?: string;
  image_url?: string;
  onboarded?: boolean;
};

type ChatSessionItem = {
  session_id: string;
  last_message?: string;
  last_role?: string;
  last_created_at?: string;
};

type SourceGroup = {
  id: string;
  label: string;
  files: string[];
};

const initialMessages: Message[] = [
  {
    id: "1",
    role: "assistant",
    text: "Hello! I am your AI Teaching Assistant. How can I help you today?",
  }
];

const createSessionId = () => `web_session_${Date.now()}`;

type RoadmapItemPreview = {
  id: string;
  topic: string;
  progress: number;
  priority?: "high" | "medium" | "low";
};

export default function StudentChat() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isProfileLoading, setIsProfileLoading] = useState(true);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [chatSessionId, setChatSessionId] = useState(createSessionId());
  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [showSessions, setShowSessions] = useState(false);
  const [sourceGroups, setSourceGroups] = useState<SourceGroup[]>([]);
  const [preferredSources, setPreferredSources] = useState<string[]>([]);
  const [showSourcePicker, setShowSourcePicker] = useState(false);
  const [activeSourceGroupId, setActiveSourceGroupId] = useState("");
  const [roadmapItems, setRoadmapItems] = useState<RoadmapItemPreview[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  useEffect(() => {
    const loadProfile = async () => {
      setIsProfileLoading(true);
      try {
        const response = await fetch("/api/users/me", { cache: "no-store" });
        if (!response.ok) {
          const errText = await response.text();
          console.error("Profile API Error:", response.status, errText);
          alert(`Lỗi API Profile (${response.status}): ${errText}`);
          return;
        }
        const payload = await response.json();
        if (payload?.profile) {
          setProfile(payload.profile);
          if (!payload.onboarded) {
            setIsRedirecting(true);
            router.replace("/signup");
            return;
          }
        } else {
          setIsRedirecting(true);
          router.replace("/signup");
          return;
        }
      } catch (error) {
        console.error("Failed to load profile", error);
        alert("Failed to load profile: " + String(error));
      } finally {
        setIsProfileLoading(false);
      }
    };

    const loadHistory = async () => {
      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "";

      if (!identity) return;

      try {
        const response = await fetch(
          `/api/chat/history?user_id=${encodeURIComponent(identity)}&session_id=${encodeURIComponent(chatSessionId)}&limit=30`,
          { cache: "no-store" }
        );
        if (!response.ok) return;

        const payload = await response.json();
        const historyItems = (payload?.items || []) as Array<{ role?: string; content?: string }>;
        if (!historyItems.length) {
          setMessages(initialMessages);
          return;
        }

        setMessages(
          historyItems.map((item, idx) => ({
            id: `h-${idx + 1}`,
            role: item.role === "assistant" ? "assistant" : "user",
            text: item.content || "",
          }))
        );
      } catch (error) {
        console.error("Failed to load chat history", error);
      }
    };

    const loadSessions = async () => {
      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "";
      if (!identity) return;
      try {
        const response = await fetch(
          `/api/chat/sessions?user_id=${encodeURIComponent(identity)}&limit=30`,
          { cache: "no-store" }
        );
        if (!response.ok) return;
        const payload = await response.json();
        setSessions(payload?.items || []);
      } catch (error) {
        console.error("Failed to load chat sessions", error);
      }
    };

    const loadSources = async () => {
      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "";
      if (!identity) return;
      try {
        const [membershipsRes, uploadsRes] = await Promise.all([
          fetch(`/api/classes?user_id=${encodeURIComponent(identity)}&role=student`, { cache: "no-store" }),
          fetch(`/api/uploads?user_id=${encodeURIComponent(identity)}`, { cache: "no-store" }),
        ]);

        const membershipsData = membershipsRes.ok ? await membershipsRes.json() : { items: [] };
        const uploadsData = uploadsRes.ok ? await uploadsRes.json() : { items: [] };

        const approvedClasses = (membershipsData.items || [])
          .filter((m: { status?: string; class?: { id?: string; name?: string } }) => m.status === "approved" && m.class?.id)
          .map((m: { class: { id: string; name?: string } }) => ({ id: m.class.id, name: m.class.name || "Unknown class" }));

        const classFileResults = await Promise.all(
          approvedClasses.map(async (c: { id: string; name: string }) => {
            const res = await fetch(`/api/class-files?user_id=${encodeURIComponent(identity)}&class_id=${encodeURIComponent(c.id)}`, { cache: "no-store" });
            const data = res.ok ? await res.json() : { items: [] };
            const files = (data.items || []).map((f: { original_filename?: string }) => String(f.original_filename || "")).filter(Boolean);
            return { id: `class:${c.id}`, label: c.name, files } as SourceGroup;
          })
        );

        const myUploadFiles = (uploadsData.items || [])
          .map((f: { filename?: string }) => String(f.filename || ""))
          .filter(Boolean);

        const groups: SourceGroup[] = [
          ...classFileResults.filter((g) => g.files.length > 0),
          { id: "personal", label: "My uploads", files: myUploadFiles },
        ].filter((g) => g.files.length > 0);

        setSourceGroups(groups);
      } catch (error) {
        console.error("Failed to load chat sources", error);
      }
    };

    const loadRoadmapPreview = async () => {
      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "";
      if (!identity) return;
      try {
        const response = await fetch(`/api/roadmap?user_id=${encodeURIComponent(identity)}`, { cache: "no-store" });
        if (!response.ok) return;
        const payload = await response.json();
        const items = (payload?.items || []) as Array<{ id?: string; topic?: string; progress?: number; priority?: "high" | "medium" | "low" }>;
        setRoadmapItems(
          items.slice(0, 4).map((item, idx) => ({
            id: String(item.id || `rm-preview-${idx + 1}`),
            topic: String(item.topic || "Roadmap item"),
            progress: Math.max(0, Math.min(Number(item.progress || 0), 100)),
            priority: item.priority,
          }))
        );
      } catch (error) {
        console.error("Failed to load roadmap preview", error);
      }
    };

    const bootstrap = async () => {
      setIsBootstrapping(true);
      try {
        await Promise.all([loadProfile(), loadHistory(), loadSessions(), loadSources(), loadRoadmapPreview()]);
      } finally {
        setIsBootstrapping(false);
      }
    };

    if (status === "authenticated") {
      bootstrap();
    }
  }, [status, session, chatSessionId]);

  // Shared send handler (used by both form submit and Enter key)
  const send = async () => {
    if (!draft.trim() || isSending) return;

    const userMessage = draft.trim();
    const tagSuffix = preferredSources.length
      ? `\n\n[Tagged files: ${preferredSources.join(", ")}]`
      : "";

    setMessages((current) => {
      const userId = String(current.length + 1);
      const assistantId = String(current.length + 2);
      return [
        ...current,
        { id: userId, role: "user", text: userMessage + tagSuffix },
        { id: assistantId, role: "assistant", text: "Thinking..." },
      ];
    });
    setIsSending(true);
    setDraft("");

    try {
      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "anonymous_user";

      const payload = {
        message: userMessage,
        user_id: identity,
        session_id: chatSessionId,
        preferred_sources: preferredSources,
      };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 20000);

      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok || !response.body) {
        let detail = "";
        try {
          detail = await response.text();
        } catch {
          detail = "";
        }

        // Fallback to non-stream endpoint for transient backend/network issues
        const fallback = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!fallback.ok) {
          const fallbackDetail = await fallback.text().catch(() => "");
          throw new Error(
            `Stream failed (${response.status}). ${detail || ""} Fallback failed (${fallback.status}). ${fallbackDetail || ""}`
          );
        }

        const fallbackJson = await fallback.json();
        const fallbackReply = String(fallbackJson?.reply || "").trim() || "Agent did not return a response.";
        setMessages((current) => {
          const next = [...current];
          const lastAssistantIndex = [...next]
            .map((m, idx) => ({ m, idx }))
            .reverse()
            .find(({ m }) => m.role === "assistant")?.idx;
          if (lastAssistantIndex === undefined) return current;
          next[lastAssistantIndex] = {
            ...next[lastAssistantIndex],
            text: fallbackReply,
          };
          return next;
        });
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let renderedText = "";
      let pendingText = "";
      let streamDone = false;

      const flushTimer = setInterval(() => {
        if (!pendingText.length) {
          if (streamDone) clearInterval(flushTimer);
          return;
        }

        const take = Math.min(4, pendingText.length);
        renderedText += pendingText.slice(0, take);
        pendingText = pendingText.slice(take);

        setMessages((current) => {
          const next = [...current];
          const lastAssistantIndex = [...next]
            .map((m, idx) => ({ m, idx }))
            .reverse()
            .find(({ m }) => m.role === "assistant")?.idx;

          if (lastAssistantIndex === undefined) return current;
          next[lastAssistantIndex] = {
            ...next[lastAssistantIndex],
            text: renderedText || "Agent is thinking...",
          };
          return next;
        });
      }, 28);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        pendingText += decoder.decode(value, { stream: true });
      }

      pendingText += decoder.decode();
      streamDone = true;

      // Wait until flush loop empties pending buffer
      while (pendingText.length > 0) {
        await new Promise((resolve) => setTimeout(resolve, 20));
      }

      if (!renderedText.trim()) {
        setMessages((current) => {
          const next = [...current];
          const lastAssistantIndex = [...next]
            .map((m, idx) => ({ m, idx }))
            .reverse()
            .find(({ m }) => m.role === "assistant")?.idx;
          if (lastAssistantIndex === undefined) return current;
          next[lastAssistantIndex] = {
            ...next[lastAssistantIndex],
            text: "Agent did not return a response.",
          };
          return next;
        });
      }
    } catch (error) {
      console.error(error);
      setMessages((current) => [
        ...current,
        {
          id: String(current.length + 1),
          role: "assistant",
          text: "Connection error to Agent API. Please try again.",
        },
      ]);
    } finally {
      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "";
      if (identity) {
        fetch(`/api/chat/sessions?user_id=${encodeURIComponent(identity)}&limit=30`, { cache: "no-store" })
          .then((res) => (res.ok ? res.json() : null))
          .then((payload) => {
            if (payload?.items) setSessions(payload.items);
          })
          .catch(() => undefined);
      }
      setIsSending(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    send();
  };

  // Press Enter to send, Shift+Enter for a new line
  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || isUploading) return;

    const identity = session?.user?.email || session?.user?.name || "";
    if (!identity) {
      setMessages((current) => [
        ...current,
        { id: String(current.length + 1), role: "assistant", text: "You need to sign in before uploading files." },
      ]);
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("user_id", identity);

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");
      const result = await response.json();

      setMessages((current) => [
        ...current,
        {
          id: String(current.length + 1),
          role: "assistant",
          text: `Uploaded: ${result.filename} (${Math.round(result.size / 1024)} KB).`,
        },
      ]);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: String(current.length + 1),
          role: "assistant",
          text: "File upload failed. Please try again.",
        },
      ]);
    } finally {
      setIsUploading(false);
      if (event.target) event.target.value = "";
    }
  };

  if (status === "loading" || isBootstrapping || isRedirecting) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 gap-4">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
        <p className="text-sm font-medium text-slate-600">Loading backend data...</p>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 gap-4">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
        <p className="text-sm font-medium text-slate-600">Redirecting to login...</p>
      </div>
    );
  }

  const startNewConversation = () => {
    if (isSending) return;
    setDraft("");
    setMessages(initialMessages);
    setChatSessionId(createSessionId());
    setShowSessions(false);
  };

  const selectSession = (sessionId: string) => {
    if (!sessionId || isSending) return;
    setDraft("");
    setChatSessionId(sessionId);
    setShowSessions(false);
  };

  const togglePreferredSource = (source: string) => {
    setPreferredSources((current) =>
      current.includes(source)
        ? current.filter((s) => s !== source)
        : [...current, source]
    );
  };

  const activeSourceGroup = sourceGroups.find((g) => g.id === activeSourceGroupId) || null;

  return (
    <MainLayout role="student">

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.9fr] h-[calc(100vh-150px)]">
        <div className="flex flex-col rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft h-full overflow-hidden">
          <div className="mb-6 flex shrink-0 items-start justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-brand-600">
                Student Chat
              </p>
              <h1 className="mt-3 text-3xl font-semibold text-slate-950">
                Ask your AI teaching assistant
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <button
                id="chat-history-toggle-btn"
                type="button"
                onClick={() => setShowSessions((v) => !v)}
                className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
              >
                Old chats
              </button>
              <button
                id="new-chat-btn"
                type="button"
                onClick={startNewConversation}
                disabled={isSending}
                className="rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                New chat
              </button>
            </div>
          </div>

          {showSessions ? (
            <div className="mb-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Saved conversations</p>
              <div className="max-h-44 space-y-2 overflow-y-auto">
                {sessions.map((s) => (
                  <button
                    key={s.session_id}
                    id={`old-chat-${s.session_id}`}
                    type="button"
                    onClick={() => selectSession(s.session_id)}
                    className={`w-full rounded-xl border px-3 py-2 text-left text-sm transition ${chatSessionId === s.session_id ? "border-brand-300 bg-brand-50" : "border-slate-200 bg-white hover:bg-slate-100"}`}
                  >
                    <p className="font-medium text-slate-900">{s.last_message || "(No preview)"}</p>
                    <p className="mt-1 text-xs text-slate-500">{s.last_created_at ? new Date(s.last_created_at).toLocaleString() : s.session_id}</p>
                  </button>
                ))}
                {sessions.length === 0 ? <p className="text-sm text-slate-500">No old chats yet.</p> : null}
              </div>
            </div>
          ) : null}

          <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-2 min-h-0">
            {messages.map((message) => (
              <ChatBubble
                key={message.id}
                role={message.role as "user" | "assistant"}
                message={message.text}
                citations={message.citations}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>

          <form
            onSubmit={handleSubmit}
            className="mt-6 shrink-0 rounded-[2rem] border border-slate-200 bg-slate-50 p-4 shadow-sm"
          >
            <div className="mb-3 flex items-center gap-2">
              <button
                id="open-source-picker-btn"
                type="button"
                onClick={() => {
                  setShowSourcePicker((v) => !v);
                  setActiveSourceGroupId("");
                }}
                className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
              >
                + File
              </button>
              {preferredSources.length > 0 ? (
                <p className="text-xs text-slate-600">{preferredSources.length} file(s) tagged</p>
              ) : (
                <p className="text-xs text-slate-500">No tagged files</p>
              )}
            </div>

            {showSourcePicker ? (
              <div className="mb-3 rounded-2xl border border-slate-200 bg-white p-3">
                {!activeSourceGroup ? (
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Choose source group</p>
                    {sourceGroups.map((group) => (
                      <button
                        key={group.id}
                        id={`source-group-${group.id}`}
                        type="button"
                        onClick={() => setActiveSourceGroupId(group.id)}
                        className="w-full rounded-xl border border-slate-200 px-3 py-2 text-left text-sm text-slate-800 transition hover:bg-slate-50"
                      >
                        {group.label}
                      </button>
                    ))}
                    {sourceGroups.length === 0 ? <p className="text-xs text-slate-500">No files available yet.</p> : null}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <button
                      id="source-group-back-btn"
                      type="button"
                      onClick={() => setActiveSourceGroupId("")}
                      className="text-xs font-semibold text-brand-700"
                    >
                      ← Back
                    </button>
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">{activeSourceGroup.label}</p>
                    <div className="flex max-h-28 flex-wrap gap-2 overflow-y-auto">
                      {activeSourceGroup.files.map((source) => {
                        const selected = preferredSources.includes(source);
                        return (
                          <button
                            key={`${activeSourceGroup.id}-${source}`}
                            id={`source-tag-${source}`}
                            type="button"
                            onClick={() => togglePreferredSource(source)}
                            className={`rounded-full border px-3 py-1 text-xs transition ${selected ? "border-brand-500 bg-brand-100 text-brand-800" : "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"}`}
                          >
                            {source}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ) : null}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <label className="flex-1">
                <span className="sr-only">Ask a question</span>
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={2}
                  placeholder="Ask a question or attach a file for context..."
                  className="min-h-[96px] w-full resize-none rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-900 shadow-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
              </label>
              <div className="flex shrink-0 flex-col items-stretch gap-3 sm:w-64">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="inline-flex items-center justify-center gap-2 rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Paperclip className="h-4 w-4" />
                  {isUploading ? "Uploading…" : "Attach"}
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  accept=".pdf,.txt,.md,.doc,.docx"
                  onChange={handleFileUpload}
                />
                <button
                  type="submit"
                  disabled={isSending}
                  className="inline-flex items-center justify-center gap-2 rounded-3xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {isSending ? "Sending…" : "Send"}
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </form>
        </div>

        <aside className="space-y-6 overflow-y-auto h-full pr-2">
          <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-brand-600">
                  Review roadmap
                </p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                  Suggested topics
                </h2>
              </div>
              <div className="rounded-3xl bg-blue-50 px-3 py-2 text-xs font-semibold text-blue-700">
                Based on your gaps
              </div>
            </div>

            <div className="mt-6 space-y-4">
              {roadmapItems.map((item) => (
                <div
                  key={item.id}
                  className="rounded-3xl border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-slate-900">
                        {item.topic}
                      </p>
                      <p className="text-sm text-slate-600">Review priority {item.priority ? `• ${item.priority}` : ""}</p>
                    </div>
                    <div className="text-sm font-semibold text-brand-700">
                      {item.progress}%
                    </div>
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-brand-600"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                </div>
              ))}
              {roadmapItems.length === 0 ? (
                <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                  No roadmap yet. Generate one in Roadmap page.
                </div>
              ) : null}
            </div>
          </div>
        </aside>
      </section>
    </MainLayout>
  );
}
