import type { SourceRef } from "./types";

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "sources"; sources: SourceRef[] }
  | { type: "refusal"; message: string }
  | { type: "error"; message: string }
  | { type: "done" };

export type ChatCallbacks = {
  onToken?: (text: string) => void;
  onSources?: (sources: SourceRef[]) => void;
  onRefusal?: (message: string) => void;
  onError?: (message: string) => void;
  onDone?: () => void;
};

// fetch-based SSE parser — EventSource can't POST or carry cookies.
export async function streamChat(
  question: string,
  cb: ChatCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch("/api/chat", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    cb.onError?.(message);
    cb.onDone?.();
    return;
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
        detail = body.detail[0].msg;
      }
    } catch {
      /* ignore */
    }
    cb.onError?.(detail);
    cb.onDone?.();
    return;
  }

  if (!resp.body) {
    cb.onError?.("No response body");
    cb.onDone?.();
    return;
  }

  const reader = resp.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += value;
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6);
        if (!raw) continue;
        let evt: ChatEvent;
        try {
          evt = JSON.parse(raw) as ChatEvent;
        } catch {
          continue;
        }
        dispatch(evt, cb);
        if (evt.type === "done") return;
      }
    }
  } catch (e) {
    if ((e as { name?: string }).name === "AbortError") return;
    cb.onError?.(e instanceof Error ? e.message : String(e));
  } finally {
    cb.onDone?.();
  }
}

function dispatch(evt: ChatEvent, cb: ChatCallbacks): void {
  switch (evt.type) {
    case "token":
      cb.onToken?.(evt.text);
      return;
    case "sources":
      cb.onSources?.(evt.sources);
      return;
    case "refusal":
      cb.onRefusal?.(evt.message);
      return;
    case "error":
      cb.onError?.(evt.message);
      return;
    case "done":
      return;
  }
}
