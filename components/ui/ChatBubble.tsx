import { MessageCircle, FileText, User } from "lucide-react";

interface ChatBubbleProps {
  role: "user" | "assistant";
  message: string;
  citations?: string[];
}

export default function ChatBubble({
  role,
  message,
  citations = [],
}: ChatBubbleProps) {
  const isAssistant = role === "assistant";

  return (
    <div
      className={`group relative rounded-[24px] p-5 shadow-[0_2px_8px_rgba(15,23,42,0.04)] ${isAssistant ? "bg-[#0F172A] text-white" : "bg-[#EEF2FF] text-[#1E1B4B]"} ${isAssistant ? "self-start" : "self-end"} w-full sm:max-w-[85%]`}
    >
      <div className={`flex items-center gap-3 text-xs font-bold uppercase tracking-wider ${isAssistant ? "text-slate-400" : "text-indigo-400"}`}>
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
      <div
        className={`mt-3 text-[15px] leading-relaxed whitespace-pre-wrap ${isAssistant ? "text-slate-200" : "text-slate-800"}`}
      >
        {message}
      </div>
      {citations.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {citations.map((citation) => (
            <span
              key={citation}
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-xs text-slate-100"
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
