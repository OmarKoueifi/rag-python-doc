import Markdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { BookText, User } from "lucide-react";
import clsx from "clsx";

import type { SourceRef } from "../lib/types";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceRef[];
  isStreaming?: boolean;
  isRefusal?: boolean;
  isError?: boolean;
};

export function ChatMessageView({ message }: { message: ChatMessage }) {
  if (message.role === "user") {
    return <UserMessage content={message.content} />;
  }
  return (
    <AssistantMessage
      content={message.content}
      sources={message.sources}
      isStreaming={message.isStreaming ?? false}
      isRefusal={message.isRefusal ?? false}
      isError={message.isError ?? false}
    />
  );
}

function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex gap-3 justify-end">
      <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-accent-500 text-white px-4 py-2.5 text-[15px] whitespace-pre-wrap">
        {content}
      </div>
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-ink-200 flex items-center justify-center">
        <User className="w-4 h-4 text-ink-600" />
      </div>
    </div>
  );
}

function AssistantMessage({
  content,
  sources,
  isStreaming,
  isRefusal,
  isError,
}: {
  content: string;
  sources?: SourceRef[];
  isStreaming: boolean;
  isRefusal: boolean;
  isError: boolean;
}) {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-ink-900 flex items-center justify-center">
        <BookText className="w-4 h-4 text-accent-100" />
      </div>
      <div className="flex-1 min-w-0">
        <div
          className={clsx(
            "rounded-2xl rounded-tl-sm px-4 py-3 border",
            isError && "bg-red-50 border-red-200 text-red-800",
            isRefusal && "bg-amber-50 border-amber-200 text-amber-900",
            !isError && !isRefusal && "bg-white border-ink-200",
          )}
        >
          {isError || isRefusal ? (
            <p className="text-[15px]">{content}</p>
          ) : (
            <div className={clsx("prose-chat", isStreaming && "typing-cursor")}>
              {content ? (
                <Markdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                >
                  {content}
                </Markdown>
              ) : (
                <span className="text-ink-400">Thinking…</span>
              )}
            </div>
          )}
        </div>
        {sources && sources.length > 0 && <SourcesFooter sources={sources} />}
      </div>
    </div>
  );
}

function SourcesFooter({ sources }: { sources: SourceRef[] }) {
  return (
    <div className="mt-2 pl-1">
      <div className="text-xs font-medium text-ink-500 uppercase tracking-wide mb-1.5">
        Sources
      </div>
      <ul className="space-y-1">
        {sources.map((s) => (
          <li key={s.rank} className="flex gap-2 items-start text-[13px]">
            <span className="flex-shrink-0 w-5 text-ink-400 font-mono">
              [{s.rank}]
            </span>
            <div className="min-w-0">
              <a
                href={s.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent-600 hover:text-accent-700 underline decoration-accent-200 hover:decoration-accent-500 truncate inline-block max-w-full"
              >
                {s.heading_path}
              </a>
              <div className="text-ink-400 text-xs">
                <span className="font-mono">{s.module}</span> ·{" "}
                sim {s.similarity.toFixed(2)}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
