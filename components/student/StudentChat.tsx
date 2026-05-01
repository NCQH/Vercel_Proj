"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import { Paperclip, Send, Sparkles, BookOpen } from "lucide-react";
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

const initialMessages: Message[] = [
  {
    id: "1",
    role: "assistant",
    text: "Hello! I am your AI Teaching Assistant. How can I help you today?",
  }
];

const roadmapItems = [
  { title: "Formative vs Summative", progress: 72 },
  { title: "Macro Review: GDP & Inflation", progress: 53 },
  { title: "Citation Tracking Techniques", progress: 85 },
  { title: "Exam Prep: Lecture 04", progress: 34 },
];

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
  const [isAccountMenuOpen, setIsAccountMenuOpen] = useState(false);
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
        if (!response.ok) return;
        const payload = await response.json();
        if (payload?.profile) {
          setProfile(payload.profile);
        }
      } catch (error) {
        console.error("Failed to load profile", error);
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
          `/api/chat/history?user_id=${encodeURIComponent(identity)}&session_id=web_session&limit=30`,
          { cache: "no-store" }
        );
        if (!response.ok) return;

        const payload = await response.json();
        const historyItems = (payload?.items || []) as Array<{ role?: string; content?: string }>;
        if (!historyItems.length) return;

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

    const bootstrap = async () => {
      setIsBootstrapping(true);
      try {
        await Promise.all([loadProfile(), loadHistory()]);
      } finally {
        setIsBootstrapping(false);
      }
    };

    if (status === "authenticated") {
      bootstrap();
    }
  }, [status, session]);

  // Shared send handler (used by both form submit and Enter key)
  const send = async () => {
    if (!draft.trim() || isSending) return;

    const userMessage = draft.trim();

    setMessages((current) => {
      const userId = String(current.length + 1);
      const assistantId = String(current.length + 2);
      return [
        ...current,
        { id: userId, role: "user", text: userMessage },
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
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage, user_id: identity }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Failed to connect to backend stream");
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
          text: "Connection error to Agent API. Please check the server.",
        },
      ]);
    } finally {
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
      <div className="fixed right-6 top-5 z-50">
        <div className="relative">
          <button
            id="account-menu-toggle"
            type="button"
            onClick={() => setIsAccountMenuOpen((prev) => !prev)}
            className="flex items-center rounded-full border border-slate-300 bg-white p-1.5 shadow-sm transition hover:shadow"
          >
            <div className="h-8 w-8 overflow-hidden rounded-full bg-brand-100 ring-1 ring-slate-200">
              {(profile?.image_url || session?.user?.image) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={profile?.image_url || session?.user?.image || ""}
                  alt="User avatar"
                  className="h-full w-full object-cover"
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-xs font-semibold text-brand-700">
                  {(profile?.full_name || session?.user?.name || "U").slice(0, 1).toUpperCase()}
                </div>
              )}
            </div>
          </button>

          {isAccountMenuOpen ? (
            <div className="absolute right-0 z-20 mt-2 w-72 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Account</p>
              <p className="mt-2 text-sm font-semibold text-slate-900">
                {profile?.full_name || session?.user?.name || "Unknown User"}
              </p>
              <p className="text-xs text-slate-600">
                {profile?.email || session?.user?.email || "No email"}
              </p>

              <div className="mt-4 grid gap-2 text-sm">
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                  <span className="text-slate-500">Class</span>
                  <span className="font-medium text-slate-900">
                    {isProfileLoading ? "Loading..." : profile?.class_name || "Not set"}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2">
                  <span className="text-slate-500">Onboarding</span>
                  <span className={`font-medium ${profile?.onboarded ? "text-emerald-700" : "text-amber-700"}`}>
                    {profile?.onboarded ? "Completed" : "Pending"}
                  </span>
                </div>
              </div>

              <button
                id="logout-btn"
                type="button"
                onClick={() => signOut({ callbackUrl: "/login" })}
                className="mt-4 w-full rounded-full border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                Sign out
              </button>
            </div>
          ) : null}
        </div>
      </div>

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
            <div className="rounded-3xl bg-brand-50 px-4 py-3 text-sm font-semibold text-brand-700">
              Live response mode
            </div>
          </div>

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
                  key={item.title}
                  className="rounded-3xl border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-slate-900">
                        {item.title}
                      </p>
                      <p className="text-sm text-slate-600">Review priority</p>
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
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200 bg-brand-950 p-6 text-white shadow-soft">
            <div className="flex items-center gap-3 text-sm font-semibold uppercase tracking-[0.24em] text-blue-200">
              <Sparkles className="h-4 w-4" />
              Study insight
            </div>
            <div className="mt-4 space-y-3 text-sm leading-6 text-slate-200">
              <p>
                Students answering similar questions improved retention by 23%
                when they reviewed the recommended lecture references.
              </p>
              <p>
                Focus on the top gap areas in your next session and compare with
                the AI-suggested citations.
              </p>
            </div>
          </div>
        </aside>
      </section>
    </MainLayout>
  );
}
