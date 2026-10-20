// The local Python API (api/main.py): Ask TOPIK and the Writing checker. Runs on this Mac only.
export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
export const API_START = ".venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000";

// Phone mode: the API also needs the secret key (from the cookie the proxy set).
function keyHeader(): Record<string, string> {
  const m = typeof document !== "undefined" ? document.cookie.match(/(?:^|; )phone_key=([^;]+)/) : null;
  return m ? { "X-Key": decodeURIComponent(m[1]) } : {};
}

export async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { headers: keyHeader() });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...keyHeader() },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

// Same rule as writing/rules.py: every character incl. spaces; paragraph breaks are not counted.
export function cells(text: string) {
  return text.trim().split("\n").reduce((n, p) => n + p.trim().length, 0);
}
