"use client";

import { useEffect, useState } from "react";
import { Paperclip, Send, Sparkles, BookOpen } from "lucide-react";
import ChatBubble from "../ui/ChatBubble";
import MainLayout from "../app-shell/MainLayout";

const initialMessages = [
  {
    id: "1",
    role: "user",
    text: "Can you explain the difference between formative assessment and summative assessment?",
  },
  {
    id: "2",
    role: "assistant",
    text: "Formative assessment supports learning with ongoing feedback during a course, while summative assessment evaluates performance at the end of a module. Use formative checks to adjust learning and summative tasks to certify mastery.",
    citations: ["Slide 12", "Page 45"],
  },
  {
    id: "3",
    role: "user",
    text: "What should I review before the next lecture on macroeconomics?",
  },
  {
    id: "4",
    role: "assistant",
    text: "Review the key definitions for GDP, inflation, and monetary policy. Pay special attention to the example in lecture 03 and the 02:15 case study.",
    citations: ["Lecture 03", "02:15 timestamp"],
  },
];

const roadmapItems = [
  { title: "Formative vs Summative", progress: 72 },
  { title: "Macro Review: GDP & Inflation", progress: 53 },
  { title: "Citation Tracking Techniques", progress: 85 },
  { title: "Exam Prep: Lecture 04", progress: 34 },
];

export default function StudentChat() {
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    const timer = setTimeout(
      () => {
        if (isSending) {
          setMessages((current) => [
            ...current,
            {
              id: String(current.length + 1),
              role: "assistant",
              text: "Great question! I recommend reviewing the previous module summary and focusing on the example citations in your study notes.",
              citations: ["Summary page", "Slide 07"],
            },
          ]);
          setIsSending(false);
          setDraft("");
        }
      },
      isSending ? 700 : 0,
    );

    return () => clearTimeout(timer);
  }, [isSending]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft.trim()) {
      return;
    }

    setMessages((current) => [
      ...current,
      { id: String(current.length + 1), role: "user", text: draft.trim() },
    ]);
    setIsSending(true);
  };

  return (
    <MainLayout role="student">
      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.9fr]">
        <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-soft">
          <div className="mb-6 flex items-start justify-between gap-4">
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

          <div className="flex flex-col gap-4">
            {messages.map((message) => (
              <ChatBubble
                key={message.id}
                role={message.role as "user" | "assistant"}
                message={message.text}
                citations={message.citations}
              />
            ))}
          </div>

          <form
            onSubmit={handleSubmit}
            className="mt-6 rounded-[2rem] border border-slate-200 bg-slate-50 p-4 shadow-sm"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <label className="flex-1">
                <span className="sr-only">Ask a question</span>
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  rows={2}
                  placeholder="Ask a question or attach a file for context..."
                  className="min-h-[96px] w-full resize-none rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-900 shadow-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                />
              </label>
              <div className="flex shrink-0 flex-col items-stretch gap-3 sm:w-64">
                <button
                  type="button"
                  className="inline-flex items-center justify-center gap-2 rounded-3xl border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
                >
                  <Paperclip className="h-4 w-4" />
                  Attach
                </button>
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

        <aside className="space-y-6">
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
