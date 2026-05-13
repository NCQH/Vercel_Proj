"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Paperclip, Send } from "lucide-react";
import { apiClient, type ChatSessionItem, type ClassMembership, type RoadmapPriority } from "../../lib/api-client";
import ChatBubble from "../ui/ChatBubble";
import MainLayout from "../app-shell/MainLayout";
import { useToast } from "../ui/ToastProvider";

type Message = {
  id: string;
  role: string;
  text: string;
  citations?: string[];
  isThinking?: boolean;
};


type UserProfile = {
  full_name: string;
  class_name: string;
  email?: string;
  image_url?: string;
  onboarded?: boolean;
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
const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;
const ALLOWED_UPLOAD_EXTENSIONS = new Set(["pdf", "txt", "md", "doc", "docx", "pptx", "xlsx", "xls"]);

type RoadmapItemPreview = {
  id: string;
  topic: string;
  progress: number;
  priority?: RoadmapPriority;
};

export default function StudentChat() {
  const { data: session, status } = useSession();
  const { showToast } = useToast();
  const router = useRouter();
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isProfileLoading, setIsProfileLoading] = useState(true);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [chatSessionId, setChatSessionId] = useState(createSessionId());
  const [sessions, setSessions] = useState<ChatSessionItem[]>([]);
  const [showSessions, setShowSessions] = useState(true);
  const [sourceGroups, setSourceGroups] = useState<SourceGroup[]>([]);
  const [preferredSources, setPreferredSources] = useState<string[]>([]);
  const [showSourcePicker, setShowSourcePicker] = useState(false);
  const [activeSourceGroupId, setActiveSourceGroupId] = useState("");
  const [roadmapItems, setRoadmapItems] = useState<RoadmapItemPreview[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadSources = async () => {
    const identity =
      (session?.user as { id?: string } | undefined)?.id ||
      session?.user?.email ||
      session?.user?.name ||
      "";
    if (!identity) return;
    try {
      const [membershipsData, uploadsData] = await Promise.all([
        apiClient.classes.list("student"),
        apiClient.uploads.list(),
      ]);

      const approvedClasses = ((membershipsData.items || []) as ClassMembership[])
        .filter((m) => m.status === "approved" && m.class?.id)
        .map((m) => ({ id: String(m.class?.id || ""), name: m.class?.name || "Unknown class" }));

      const classFileResults = await Promise.all(
        approvedClasses.map(async (c: { id: string; name: string }) => {
          const data = await apiClient.classes.listFiles(c.id);
          const files = (data.items || []).map((f: { original_filename?: string }) => String(f.original_filename || "")).filter(Boolean);
          return { id: `class:${c.id}`, label: c.name, files } as SourceGroup;
        })
      );

      const myUploadFiles = (uploadsData.items || [])
        .map((f: { original_filename?: string; filename?: string }) =>
          String(f.original_filename || f.filename || "")
        )
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
          showToast({
            type: "error",
            title: "Profile load failed",
            message: `Server returned ${response.status}. Please refresh or sign in again.`,
          });
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
        showToast({
          type: "error",
          title: "Profile load failed",
          message: error instanceof Error ? error.message : String(error),
        });
      } finally {
        setIsProfileLoading(false);
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
        const payload = await apiClient.chat.getSessions(30);
        setSessions(payload?.items || []);
      } catch (error) {
        console.error("Failed to load chat sessions", error);
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
        const payload = await apiClient.roadmap.get();
        const items = payload.items || [];
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
        await Promise.all([loadProfile(), loadSessions(), loadSources(), loadRoadmapPreview()]);
      } finally {
        setIsBootstrapping(false);
      }
    };

    if (status === "authenticated") {
      bootstrap();
    }
  }, [status, session]);

  useEffect(() => {
    const loadHistory = async () => {
      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "";

      if (!identity) return;

      setIsLoadingHistory(true);
      try {
        const payload = await apiClient.chat.getHistory(chatSessionId, 30);
        const historyItems = payload.items || [];
        if (!historyItems.length) {
          setMessages(initialMessages);
          return;
        }

        const mappedHistory = historyItems.map((item, idx) => ({
          id: `h-${idx + 1}`,
          role: item.role === "assistant" ? "assistant" : "user",
          text: item.content || "",
          citations: Array.isArray((item as { citations?: unknown }).citations)
            ? ((item as { citations?: unknown[] }).citations || [])
              .map((c) => String(c || "").trim())
              .filter(Boolean)
            : [],
        })) as Message[];

        setMessages(mappedHistory);
      } catch (error) {
        console.error("Failed to load chat history", error);
      } finally {
        setIsLoadingHistory(false);
      }
    };

    if (status === "authenticated") {
      loadHistory();
    }
  }, [status, session, chatSessionId]);

  // Shared send handler (used by form submit, Enter key, and suggested prompts)
  const send = async (overrideMessage?: string) => {
    const messageToSend = (overrideMessage ?? draft).trim();
    if (!messageToSend || isSending) return;

    const userMessage = messageToSend;
    const tagSuffix = preferredSources.length
      ? `\n\n[Tagged files: ${preferredSources.join(", ")}]`
      : "";

    let stepText = "Connecting to agent...";
    let preStreamTimer: ReturnType<typeof setInterval> | undefined;

    const updateThinkingMessage = (nextText: string) => {
      setMessages((current) => {
        const next = [...current];
        const lastAssistantIndex = [...next]
          .map((m, idx) => ({ m, idx }))
          .reverse()
          .find(({ m }) => m.role === "assistant")?.idx;
        if (lastAssistantIndex === undefined) return current;
        next[lastAssistantIndex] = {
          ...next[lastAssistantIndex],
          text: nextText,
          isThinking: true,
        };
        return next;
      });
    };

    setMessages((current) => {
      const userId = String(current.length + 1);
      const assistantId = String(current.length + 2);
      return [
        ...current,
        { id: userId, role: "user", text: userMessage + tagSuffix },
        { id: assistantId, role: "assistant", text: stepText, isThinking: true },
      ];
    });
    setIsSending(true);
    setDraft("");

    try {
      preStreamTimer = setInterval(() => {
        updateThinkingMessage("Connecting to agent...");
      }, 2000);

      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "anonymous_user";

      const payload = {
        message: userMessage,
        session_id: chatSessionId,
        preferred_sources: preferredSources,
      };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 45000);

      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (preStreamTimer) clearInterval(preStreamTimer);

      if (!response.ok || !response.body) {
        let detail = "";
        try {
          detail = await response.text();
        } catch {
          detail = "";
        }

        // Fallback to non-stream endpoint for transient backend/network issues
        const fallbackJson = await apiClient.chat.send(payload);
        const fallbackReply = String(fallbackJson?.reply || "").trim() || "Agent did not return a response.";
        const fallbackSources = Array.isArray(fallbackJson?.sources)
          ? fallbackJson.sources.map((s: unknown) => String(s || "").trim()).filter(Boolean)
          : [];
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
            citations: fallbackSources,
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
      let rawBuffer = "";
      let streamedSources: string[] = [];
      let lastRenderedDisplay = "";
      const waitingSteps = [
        "Waiting for agent progress...",
      ];
      let waitingStepIndex = 0;
      const waitingTimer = setInterval(() => {
        if (renderedText || pendingText || streamDone) {
          clearInterval(waitingTimer);
          return;
        }
        waitingStepIndex = Math.min(waitingStepIndex + 1, waitingSteps.length - 1);
        stepText = waitingSteps[waitingStepIndex];
      }, 2200);

      const flushTimer = setInterval(() => {
        if (pendingText.length > 0) {
          renderedText += pendingText;
          pendingText = "";
        }

        const displayText = renderedText || stepText || "Agent is thinking...";
        const isThinking = !renderedText;

        if (displayText !== lastRenderedDisplay) {
          lastRenderedDisplay = displayText;
          setMessages((current) => {
            const next = [...current];
            const lastAssistantIndex = [...next]
              .map((m, idx) => ({ m, idx }))
              .reverse()
              .find(({ m }) => m.role === "assistant")?.idx;

            if (lastAssistantIndex === undefined) return current;
            next[lastAssistantIndex] = {
              ...next[lastAssistantIndex],
              text: displayText,
              isThinking: isThinking,
            };
            return next;
          });
        }

        if (streamDone && !pendingText.length) {
          clearInterval(flushTimer);
          clearInterval(waitingTimer);
        }
      }, 28);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        rawBuffer += decoder.decode(value, { stream: true });

        let lines = rawBuffer.split('\n');
        rawBuffer = lines.pop() || "";

        for (const line of lines) {
          const normalized = line.trimStart();
          if (normalized.startsWith("__STEP__:")) {
            const stepName = normalized.replace("__STEP__:", "").trim();
            if (stepName !== "Done") {
              stepText = stepName;
            }
          } else if (normalized.startsWith("__CHUNK__:")) {
            pendingText += normalized.replace("__CHUNK__:", "");
          } else if (normalized.startsWith("__SOURCES__:")) {
            const rawSources = normalized.replace("__SOURCES__:", "").trim();
            try {
              const parsed = JSON.parse(rawSources);
              if (Array.isArray(parsed)) {
                streamedSources = parsed.map((s) => String(s || "").trim()).filter(Boolean);
              }
            } catch {
              // ignore malformed source payload
            }
          } else if (normalized.trim().length > 0) {
            // Fallback for non-protocol lines (e.g. errors)
            pendingText += normalized + "\n";
          }
        }
      }

      rawBuffer += decoder.decode();
      if (rawBuffer.trim()) {
        let lines = rawBuffer.split('\n');
        for (const line of lines) {
          const normalized = line.trimStart();
          if (normalized.startsWith("__CHUNK__:")) {
            pendingText += normalized.replace("__CHUNK__:", "");
          } else if (normalized.startsWith("__SOURCES__:")) {
            const rawSources = normalized.replace("__SOURCES__:", "").trim();
            try {
              const parsed = JSON.parse(rawSources);
              if (Array.isArray(parsed)) {
                streamedSources = parsed.map((s) => String(s || "").trim()).filter(Boolean);
              }
            } catch {
              // ignore malformed source payload
            }
          } else if (normalized.trim().length > 0) {
            pendingText += normalized + "\n";
          }
        }
      }
      streamDone = true;

      // Wait until flush loop empties pending buffer
      while (pendingText.length > 0) {
        await new Promise((resolve) => setTimeout(resolve, 20));
      }

      const finalText = renderedText.trim();

      if (!finalText) {
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
            citations: streamedSources,
          };
          return next;
        });
      } else {
        setMessages((current) => {
          const next = [...current];
          const lastAssistantIndex = [...next]
            .map((m, idx) => ({ m, idx }))
            .reverse()
            .find(({ m }) => m.role === "assistant")?.idx;
          if (lastAssistantIndex === undefined) return current;
          next[lastAssistantIndex] = {
            ...next[lastAssistantIndex],
            text: finalText,
            citations: streamedSources,
          };
          return next;
        });
      }
    } catch (error) {
      console.error(error);
      setMessages((current) => {
        const next = [...current];
        const lastAssistantIndex = [...next]
          .map((m, idx) => ({ m, idx }))
          .reverse()
          .find(({ m }) => m.role === "assistant")?.idx;
        if (lastAssistantIndex === undefined) return current;
        next[lastAssistantIndex] = {
          ...next[lastAssistantIndex],
          text: "Connection error to Agent API. Please try again.",
        };
        return next;
      });
    } finally {
      if (preStreamTimer) clearInterval(preStreamTimer);
      const identity =
        (session?.user as { id?: string } | undefined)?.id ||
        session?.user?.email ||
        session?.user?.name ||
        "";
      if (identity) {
        apiClient.chat.getSessions(30)
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

    const extension = file.name.split(".").pop()?.toLowerCase() || "";
    if (!ALLOWED_UPLOAD_EXTENSIONS.has(extension)) {
      showToast({
        type: "warning",
        title: "Unsupported file type",
        message: "Please upload PDF, DOC, DOCX, PPTX, XLS, XLSX, TXT, or MD files.",
      });
      event.target.value = "";
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      showToast({
        type: "warning",
        title: "File too large",
        message: "Maximum upload size is 15 MB.",
      });
      event.target.value = "";
      return;
    }

    const identity = session?.user?.email || session?.user?.name || "";
    if (!identity) {
      showToast({
        type: "error",
        title: "Sign in required",
        message: "You need to sign in before uploading files.",
      });
      setMessages((current) => [
        ...current,
        { id: String(current.length + 1), role: "assistant", text: "You need to sign in before uploading files." },
      ]);
      return;
    }

    setIsUploading(true);
    const tempId = `upload-${Date.now()}`;
    setMessages((current) => [
      ...current,
      {
        id: tempId,
        role: "assistant",
        text: `⏳ Uploading ${file.name}...`,
      },
    ]);

    try {
      const result = await apiClient.uploads.upload(file);

      setMessages((current) =>
        current.map((msg) =>
          msg.id === tempId
            ? {
              ...msg,
              text: `✅ Uploaded: ${result.filename} (${Math.round(result.size / 1024)} KB).`,
            }
            : msg
        )
      );
      showToast({
        type: "success",
        title: "Upload complete",
        message: `${result.filename} is ready for AI retrieval.`,
      });
      await loadSources();
      if (result.filename) {
        setPreferredSources((current) => {
          if (!current.includes(result.filename)) {
            return [...current, result.filename];
          }
          return current;
        });
      }
    } catch (error) {
      setMessages((current) =>
        current.map((msg) =>
          msg.id === tempId
            ? {
              ...msg,
              text: `❌ File upload failed for ${file.name}. Please try again.`,
            }
            : msg
        )
      );
      showToast({
        type: "error",
        title: "Upload failed",
        message: `Could not upload ${file.name}. Please try again.`,
      });
    } finally {
      setIsUploading(false);
      if (event.target) event.target.value = "";
    }
  };

  useEffect(() => {
    const identity =
      (session?.user as { id?: string } | undefined)?.id ||
      session?.user?.email ||
      session?.user?.name ||
      "";
    if (!identity || !chatSessionId) return;
    try {
      const cacheKey = `chat_messages_${identity}_${chatSessionId}`;
      localStorage.setItem(cacheKey, JSON.stringify(messages));
    } catch {
      // ignore storage quota / serialize errors
    }
  }, [messages, session, chatSessionId]);

  if (status === "unauthenticated") {
    return (
      <MainLayout role="student">
        <div className="flex h-full min-h-[50vh] flex-col items-center justify-center bg-transparent gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
          <p className="text-sm font-medium text-slate-600">Redirecting to login...</p>
        </div>
      </MainLayout>
    );
  }

  if (status === "loading" || isRedirecting) {
    return (
      <MainLayout role="student">
        <div className="flex h-full min-h-[50vh] flex-col items-center justify-center bg-transparent gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
          <p className="text-sm font-medium text-slate-600">Checking authorization...</p>
        </div>
      </MainLayout>
    );
  }

  const startNewConversation = () => {
    if (isSending) return;
    setDraft("");
    setMessages(initialMessages);
    setChatSessionId(createSessionId());
  };

  const selectSession = (sessionId: string) => {
    if (!sessionId || isSending) return;
    setDraft("");
    setChatSessionId(sessionId);
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

      <section className="flex gap-6 h-[calc(100vh-150px)] min-h-0 w-full">

        {/* Left Sidebar: Chat History */}
        <aside className={`flex flex-col h-full shrink-0 transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)] overflow-hidden ${showSessions ? 'w-[240px] opacity-100 translate-x-0' : 'w-0 opacity-0 -translate-x-4'}`}>
          <div className="flex flex-col gap-4 w-[240px] h-full">
            <button
              id="new-chat-btn"
              type="button"
              onClick={startNewConversation}
              disabled={isSending}
              className="w-full flex items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 shadow-sm shrink-0"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"></path></svg>
              New Chat
            </button>

            <div className="flex-1 overflow-y-auto rounded-[24px] border border-slate-200 bg-white p-4 shadow-[0_2px_8px_rgba(15,23,42,0.04)] flex flex-col min-h-0">
              <p className="mb-4 text-xs font-bold uppercase tracking-[0.2em] text-slate-500 px-2 shrink-0">Recent Chats</p>
              <div className="space-y-1 overflow-y-auto pr-1 flex-1 min-h-0">
                {isBootstrapping ? (
                  <div className="flex justify-center p-4">
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-slate-200 border-t-brand-600" />
                  </div>
                ) : (
                  <>
                    {sessions.map((s) => (
                      <button
                        key={s.session_id}
                        id={`old-chat-${s.session_id}`}
                        type="button"
                        onClick={() => selectSession(s.session_id)}
                        className={`w-full rounded-[16px] px-3 py-2.5 text-left transition ${chatSessionId === s.session_id ? "bg-brand-50 text-brand-900" : "bg-transparent text-slate-600 hover:bg-slate-50"}`}
                      >
                        <p className="font-bold text-sm truncate">{s.last_message || "New Conversation"}</p>
                        <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">{s.last_created_at ? new Date(s.last_created_at).toLocaleDateString() : s.session_id}</p>
                      </button>
                    ))}
                    {sessions.length === 0 ? <p className="text-sm font-medium text-slate-400 px-2">No old chats.</p> : null}
                  </>
                )}
              </div>
            </div>
          </div>
        </aside>

        {/* Center: Main Chat Area */}
        <div className="flex-1 flex flex-col rounded-[2rem] border border-slate-200 bg-white p-6 shadow-[0_2px_8px_rgba(15,23,42,0.04)] h-full overflow-hidden min-h-0">
          <div className="mb-6 flex shrink-0 items-start justify-between gap-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowSessions((v) => !v)}
                className="p-2.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-500 transition shadow-sm bg-white"
                title="Toggle Sidebar"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h7"></path></svg>
              </button>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] font-bold text-brand-600">
                  Student Chat
                </p>
                <h1 className="mt-1 text-2xl font-bold text-slate-900">
                  Ask your AI assistant
                </h1>
              </div>
            </div>
          </div>

          <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-2 min-h-0">
            {isBootstrapping || isLoadingHistory ? (
              <div className="flex h-full flex-col items-center justify-center gap-4">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-brand-600" />
                <p className="text-sm font-medium text-slate-500">Loading context...</p>
              </div>
            ) : (
              <>
                {messages.map((message) => (
                  <ChatBubble
                    key={message.id}
                    role={message.role as "user" | "assistant"}
                    message={message.text}
                    citations={message.citations}
                    isThinking={message.isThinking}
                  />
                ))}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          <div className="mt-4 flex flex-wrap gap-2 shrink-0">
            <button type="button" onClick={() => send("Explain supervised learning")} className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-xs font-semibold text-slate-600 hover:bg-slate-100 transition shadow-[0_2px_8px_rgba(15,23,42,0.04)]">✨ Explain supervised learning</button>
            <button type="button" onClick={() => send("Quiz me on clustering")} className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-xs font-semibold text-slate-600 hover:bg-slate-100 transition shadow-[0_2px_8px_rgba(15,23,42,0.04)]">✨ Quiz me on clustering</button>
            <button type="button" onClick={() => send("Summarize uploaded files")} className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-xs font-semibold text-slate-600 hover:bg-slate-100 transition shadow-[0_2px_8px_rgba(15,23,42,0.04)]">✨ Summarize uploaded files</button>
            <button type="button" onClick={() => send("Generate exam questions")} className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-full text-xs font-semibold text-slate-600 hover:bg-slate-100 transition shadow-[0_2px_8px_rgba(15,23,42,0.04)]">✨ Generate exam questions</button>
          </div>

          <form
            onSubmit={handleSubmit}
            className="mt-4 shrink-0"
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
            <div className="relative flex items-center bg-[#F8FAFC] border border-slate-200 rounded-[24px] p-1.5 shadow-[0_2px_8px_rgba(15,23,42,0.04)] focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100 transition-all">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="p-3 text-slate-500 hover:text-brand-600 transition disabled:opacity-50 shrink-0"
                title="Upload file"
              >
                <Paperclip className="h-5 w-5" />
              </button>

              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder="Ask anything about ML..."
                className="w-full resize-none bg-transparent px-2 py-3.5 text-sm text-slate-900 outline-none max-h-32"
                style={{ minHeight: '52px' }}
              />

              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".pdf,.txt,.md,.doc,.docx"
                onChange={handleFileUpload}
              />

              <button
                type="submit"
                disabled={isSending || !draft.trim()}
                className="p-3 bg-brand-600 text-white rounded-full mx-1 shrink-0 hover:bg-brand-700 disabled:opacity-50 transition shadow-[0_2px_8px_rgba(15,23,42,0.04)]"
                title="Send"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </form>
        </div>

        <aside className="hidden xl:block w-[280px] shrink-0 space-y-6 overflow-y-auto h-full pr-2">
          <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] font-bold text-brand-600">
                  Review Roadmap
                </p>
                <h2 className="mt-1 text-xl font-bold text-slate-900">
                  Suggested topics
                </h2>
              </div>
              <div className="rounded-xl bg-blue-50 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-blue-700">
                Personalized
              </div>
            </div>

            <div className="mt-6 space-y-4">
              {isBootstrapping ? (
                <div className="flex justify-center p-4">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-200 border-t-brand-600" />
                </div>
              ) : (
                <>
                  {roadmapItems.map((item) => {
                    const priorityColors = {
                      high: "border-red-200 bg-red-50/50",
                      medium: "border-amber-200 bg-amber-50/50",
                      low: "border-emerald-200 bg-emerald-50/50",
                    };
                    const progressColors = {
                      high: "bg-red-500",
                      medium: "bg-amber-500",
                      low: "bg-emerald-500",
                    };
                    const colorClass = item.priority ? priorityColors[item.priority] : priorityColors.low;
                    const progressClass = item.priority ? progressColors[item.priority] : progressColors.low;

                    return (
                      <div
                        key={item.id}
                        className={`rounded-[20px] border p-4 shadow-[0_2px_8px_rgba(15,23,42,0.04)] transition hover:-translate-y-0.5 ${colorClass}`}
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="font-bold text-slate-900">
                              {item.topic}
                            </p>
                            <p className="text-xs font-medium text-slate-500 mt-1 uppercase tracking-wider">
                              Priority: {item.priority || "Low"}
                            </p>
                          </div>
                          <div className={`text-xs font-bold px-2 py-1 rounded-lg bg-white shadow-sm`}>
                            {item.progress}%
                          </div>
                        </div>
                        <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-200/50">
                          <div
                            className={`h-full rounded-full transition-all duration-1000 ${progressClass}`}
                            style={{ width: `${item.progress}%` }}
                          />
                        </div>
                        <div className="mt-4 flex gap-2">
                          <button className="flex-1 bg-white text-xs font-bold text-slate-700 py-2 rounded-xl shadow-sm border border-slate-100 hover:bg-slate-50 transition">Review Now</button>
                        </div>
                      </div>
                    );
                  })}
                  {roadmapItems.length === 0 ? (
                    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                      No roadmap yet. Generate one in Roadmap page.
                    </div>
                  ) : null}
                </>
              )}
            </div>
          </div>
        </aside>
      </section>
    </MainLayout>
  );
}
