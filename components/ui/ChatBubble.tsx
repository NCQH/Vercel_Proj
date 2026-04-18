import { MessageCircle, FileText } from "lucide-react";

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
      className={`group relative rounded-3xl p-5 shadow-soft ${isAssistant ? "bg-slate-950 text-white" : "bg-white text-slate-900"} ${isAssistant ? "self-start" : "self-end"} max-w-[90%] sm:max-w-xl`}
    >
      <div className="flex items-center gap-3 text-sm font-medium opacity-80">
        <span>{isAssistant ? "AI Assistant" : "You"}</span>
        {isAssistant ? (
          <MessageCircle className="h-4 w-4" />
        ) : (
          <FileText className="h-4 w-4" />
        )}
      </div>
      <p
        className={`mt-4 text-sm leading-7 ${isAssistant ? "text-slate-100" : "text-slate-800"}`}
      >
        {message}
      </p>
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
