import { apiFetch, getApiErrorMessage } from "./api";

export interface PreviewHistoryItem {
  role: "user" | "assistant";
  content: string;
}
export interface DoneEvent {
  wasGrounded?: boolean;
  topSimilarity?: number;
  latencyMs?: number;
  titles?: string[];
}
export interface HandoffEvent {
  reason: string;
}
export interface PreviewCallbacks {
  onToken: (t: string) => void;
  onHandoff: (e: HandoffEvent) => void;
  onDone: (e: DoneEvent) => void;
  onError: (message: string) => void;
}

export async function streamPreviewChat(
  message: string,
  history: PreviewHistoryItem[],
  cb: PreviewCallbacks,
): Promise<void> {
  const res = await apiFetch("/api/rag/chat", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok || !res.body) {
    cb.onError(await getApiErrorMessage(res, `Request failed (${res.status})`));
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const event = raw
        .split("\n")
        .find((line) => line.startsWith("event:"))
        ?.slice(6)
        .trim();
      const line = raw.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const json = line.slice(5).trim();
      if (!json) continue;

      let evt: { type: string; [k: string]: unknown };
      try {
        evt = JSON.parse(json);
      } catch {
        continue;
      }

      switch (event ?? evt.type) {
        case "token":
          cb.onToken(evt.content as string);
          break;
        case "handoff":
          cb.onHandoff({ reason: evt.reason as string });
          break;
        case "done":
          cb.onDone({
            wasGrounded:
              typeof evt.wasGrounded === "boolean" ? evt.wasGrounded : undefined,
            topSimilarity:
              typeof evt.topSimilarity === "number" ? evt.topSimilarity : undefined,
            latencyMs:
              typeof evt.latencyMs === "number" ? evt.latencyMs : undefined,
            titles: Array.isArray(evt.titles)
              ? (evt.titles.filter((title) => typeof title === "string") as string[])
              : undefined,
          });
          break;
        case "error":
          cb.onError(evt.message as string);
          break;
      }
    }
  }
}
