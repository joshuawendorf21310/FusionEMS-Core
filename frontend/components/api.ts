export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isProd = process.env.NODE_ENV === "production";
  const base =
    process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.BACKEND_URL ||
    (!isProd ? "http://localhost:8000" : undefined);

  if (!base) {
    throw new Error(
      "Backend base URL is not configured. Set NEXT_PUBLIC_BACKEND_URL (or NEXT_PUBLIC_API_URL / BACKEND_URL) in the runtime environment."
    );
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const baseNoTrailing = base.endsWith("/") ? base.slice(0, -1) : base;
  const res = await fetch(`${baseNoTrailing}${normalizedPath}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  const text = await res.text();
  let json: any = null;
  try { json = text ? JSON.parse(text) : null; } catch { /* ignore */ }
  if (!res.ok) {
    const msg = json?.detail || json?.message || `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return json as T;
}
