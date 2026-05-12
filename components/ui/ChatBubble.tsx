import { FileText, User } from "lucide-react";
import type { ReactNode } from "react";

interface ChatBubbleProps {
  role: "user" | "assistant";
  message: string;
  citations?: string[];
  isThinking?: boolean;
}

function renderInlineMarkdown(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const tokenRegex = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^\)]+\))/g;
  let lastIndex = 0;
  let key = 0;

  for (const match of text.matchAll(tokenRegex)) {
    const full = match[0];
    const index = match.index ?? 0;

    if (index > lastIndex) {
      nodes.push(text.slice(lastIndex, index));
    }

    if (full.startsWith("**") && full.endsWith("**")) {
      nodes.push(<strong key={`strong-${key++}`} className="font-semibold text-white">{full.slice(2, -2)}</strong>);
    } else if (full.startsWith("`") && full.endsWith("`")) {
      nodes.push(
        <code
          key={`code-${key++}`}
          className="rounded-md border border-white/15 bg-white/10 px-1.5 py-0.5 font-mono text-[0.9em] text-slate-100"
        >
          {full.slice(1, -1)}
        </code>
      );
    } else {
      const linkMatch = full.match(/^\[([^\]]+)\]\(([^\)]+)\)$/);
      if (linkMatch) {
        const [, label, href] = linkMatch;
        nodes.push(
          <a
            key={`link-${key++}`}
            href={href}
            target="_blank"
            rel="noreferrer"
            className="underline decoration-slate-300/70 underline-offset-2 hover:text-cyan-200"
          >
            {label}
          </a>
        );
      } else {
        nodes.push(full);
      }
    }

    lastIndex = index + full.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function renderAssistantMarkdown(message: string): ReactNode {
  const lines = message.split("\n");
  const blocks: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (!listItems.length) return;
    blocks.push(
      <ul key={`list-${blocks.length}`} className="my-2 list-disc space-y-1 pl-5 text-slate-100">
        {listItems.map((item, idx) => (
          <li key={`li-${idx}`}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>
    );
    listItems = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushList();
      continue;
    }

    if (/^[-*+]\s+/.test(line)) {
      listItems.push(line.replace(/^[-*+]\s+/, ""));
      continue;
    }

    flushList();

    if (/^###\s+/.test(line)) {
      blocks.push(
        <h3 key={`h3-${blocks.length}`} className="mt-3 text-base font-semibold text-white">
          {renderInlineMarkdown(line.replace(/^###\s+/, ""))}
        </h3>
      );
      continue;
    }

    if (/^##\s+/.test(line)) {
      blocks.push(
        <h2 key={`h2-${blocks.length}`} className="mt-3 text-lg font-semibold text-white">
          {renderInlineMarkdown(line.replace(/^##\s+/, ""))}
        </h2>
      );
      continue;
    }

    if (/^#\s+/.test(line)) {
      blocks.push(
        <h1 key={`h1-${blocks.length}`} className="mt-3 text-xl font-bold text-white">
          {renderInlineMarkdown(line.replace(/^#\s+/, ""))}
        </h1>
      );
      continue;
    }

    blocks.push(
      <p key={`p-${blocks.length}`} className="my-1 text-slate-100">
        {renderInlineMarkdown(line)}
      </p>
    );
  }

  flushList();

  return blocks.length ? blocks : <p className="text-slate-100">{message}</p>;
}

export default function ChatBubble({
  role,
  message,
  citations = [],
  isThinking = false,
}: ChatBubbleProps) {
  const isAssistant = role === "assistant";

  return (
    <div
      className={`group relative rounded-[24px] p-5 shadow-[0_2px_8px_rgba(15,23,42,0.04)] ${isAssistant ? "bg-gradient-to-br from-[#0F172A] to-[#1E293B] text-white border border-slate-700/60" : "bg-[#EEF2FF] text-[#1E1B4B] border border-indigo-100"} ${isAssistant ? "self-start" : "self-end"} w-full sm:max-w-[85%] transition-all duration-300`}
    >
      <div className={`flex items-center gap-3 text-xs font-bold uppercase tracking-wider ${isAssistant ? "text-slate-400" : "text-indigo-500"}`}>
        {isAssistant ? (
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 text-white shadow-sm">
               ✨
            </div>
            AI Assistant
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-200 text-indigo-700 shadow-sm">
               <User className="h-3.5 w-3.5" />
            </div>
            You
          </div>
        )}
      </div>
      <div className={`mt-3 text-[15px] leading-relaxed whitespace-pre-wrap transition-all duration-500 ${isAssistant ? "text-slate-100" : "text-slate-800"} ${isThinking ? "italic animate-pulse opacity-70 select-none" : ""}`}>
        {isAssistant && !isThinking ? renderAssistantMarkdown(message) : message}
      </div>
      {citations.length > 0 && !isThinking ? (
        <div className="mt-4 flex flex-wrap gap-2 border-t border-white/10 pt-3">
          {citations.map((citation) => (
            <span
              key={citation}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold text-slate-100"
              title={citation}
            >
              <FileText className="h-3.5 w-3.5" />
              {citation}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
