import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Send, Sparkles } from "lucide-react";

import { ChatMessageView, type ChatMessage } from "../components/ChatMessage";
import { streamChat } from "../lib/sse";

const EXAMPLE_QUESTIONS = [
  "How do I run multiple coroutines concurrently?",
  "What's the difference between Optional and Union in typing?",
  "How do I cancel an asyncio task cleanly?",
  "What is typing.Protocol for?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [inFlight, setInFlight] = useState(false);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const submit = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed || inFlight) return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
      };
      const assistantId = crypto.randomUUID();
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        content: "",
        isStreaming: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInput("");
      setInFlight(true);

      const patch = (updater: (m: ChatMessage) => ChatMessage) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? updater(m) : m)),
        );

      await streamChat(trimmed, {
        onToken: (text) => patch((m) => ({ ...m, content: m.content + text })),
        onSources: (sources) => patch((m) => ({ ...m, sources })),
        onRefusal: (message) =>
          patch((m) => ({
            ...m,
            content: message,
            isRefusal: true,
            isStreaming: false,
          })),
        onError: (message) =>
          patch((m) => ({
            ...m,
            content: `Something went wrong: ${message}`,
            isError: true,
            isStreaming: false,
          })),
        onDone: () => {
          patch((m) => ({ ...m, isStreaming: false }));
          setInFlight(false);
        },
      });
    },
    [inFlight],
  );

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const isSubmit =
      (e.key === "Enter" && (e.metaKey || e.ctrlKey)) ||
      (e.key === "Enter" && !e.shiftKey);
    if (isSubmit) {
      e.preventDefault();
      submit(input);
    }
  };

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [input]);

  return (
    <div className="min-h-full flex flex-col">
      <Header />
      <main
        ref={scrollerRef}
        className="flex-1 overflow-y-auto"
      >
        <div className="mx-auto w-full max-w-3xl px-4 py-6">
          {messages.length === 0 ? (
            <EmptyState onPick={(q) => submit(q)} />
          ) : (
            <div className="space-y-6">
              {messages.map((m) => (
                <ChatMessageView key={m.id} message={m} />
              ))}
            </div>
          )}
        </div>
      </main>
      <footer className="border-t border-ink-200 bg-white">
        <div className="mx-auto w-full max-w-3xl px-4 py-4">
          <div className="flex items-end gap-2 rounded-2xl border border-ink-200 bg-ink-50 focus-within:border-accent-500 focus-within:bg-white transition">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask a question about Python's asyncio or typing docs…"
              rows={1}
              maxLength={1000}
              disabled={inFlight}
              className="flex-1 bg-transparent resize-none px-4 py-3 text-[15px] outline-none placeholder:text-ink-400 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => submit(input)}
              disabled={inFlight || !input.trim()}
              className="m-1.5 rounded-xl bg-accent-500 text-white px-3 py-2 hover:bg-accent-600 disabled:bg-ink-200 disabled:text-ink-400 transition"
              aria-label="Send"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
          <p className="mt-2 text-xs text-ink-400 text-center">
            Scope: Python <code>asyncio</code> and <code>typing</code>. Answers
            cite the docs — always verify for production use.
          </p>
        </div>
      </footer>
    </div>
  );
}

function Header() {
  return (
    <header className="border-b border-ink-200 bg-white">
      <div className="mx-auto w-full max-w-3xl px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-ink-900 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-accent-100" />
          </div>
          <div>
            <div className="font-semibold text-ink-900 leading-tight">
              Ask the Python Docs
            </div>
            <div className="text-xs text-ink-500 leading-tight">
              Retrieval-grounded answers with citations
            </div>
          </div>
        </div>
        <Link
          to="/admin"
          className="text-sm text-ink-500 hover:text-ink-800 underline decoration-ink-200 hover:decoration-ink-500"
        >
          Admin
        </Link>
      </div>
    </header>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="py-12 text-center">
      <div className="mx-auto w-12 h-12 rounded-2xl bg-ink-900 flex items-center justify-center mb-4">
        <Sparkles className="w-6 h-6 text-accent-100" />
      </div>
      <h1 className="text-2xl font-semibold text-ink-900">
        Ask about Python's docs
      </h1>
      <p className="mt-2 text-ink-500 text-[15px]">
        Answers come only from the official{" "}
        <code className="bg-ink-100 rounded px-1">asyncio</code> and{" "}
        <code className="bg-ink-100 rounded px-1">typing</code> docs — with
        clickable source citations.
      </p>
      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onPick(q)}
            className="text-left rounded-xl border border-ink-200 bg-white hover:bg-ink-50 hover:border-accent-500 transition px-4 py-3 text-[14px] text-ink-700"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
