/**
 * Minimal SSE frame reader for a `fetch` response body. Not `EventSource`
 * because Clerk auth needs a `Bearer` header, which EventSource can't send.
 * Frames are `data: <json>\n\n` — exactly what Agent/backend's chat route
 * emits, nothing more general is needed.
 */
export async function parseSSEStream<T>(
  response: Response,
  onEvent: (event: T) => void,
  signal?: AbortSignal
): Promise<void> {
  const body = response.body;
  if (!body) return;

  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const abortHandler = () => reader.cancel().catch(() => {});
  signal?.addEventListener("abort", abortHandler);

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const line = frame.split("\n").find((l) => l.startsWith("data:"));
        if (!line) continue;
        const json = line.slice(5).trim();
        if (!json) continue;
        try {
          onEvent(JSON.parse(json) as T);
        } catch {
          // Malformed frame — skip rather than break the whole stream.
        }
      }
    }
  } finally {
    signal?.removeEventListener("abort", abortHandler);
  }
}
