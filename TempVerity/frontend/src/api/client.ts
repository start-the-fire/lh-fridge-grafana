export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : response.statusText;
    throw new Error(`Request failed (${response.status})${detail ? `: ${detail}` : ""}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = await response.text();
  return (body ? JSON.parse(body) : undefined) as T;
}
