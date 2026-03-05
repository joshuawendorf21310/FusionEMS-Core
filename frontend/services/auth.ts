type LoginOptions = {
  redirectTo?: string;
};

export async function login(email: string, password: string, options?: LoginOptions): Promise<void> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Authentication failed');
  }

  const data = await res.json();
  const token = data.access_token;

  // Canonical key
  localStorage.setItem('token', token);
  // Back-compat for older pages still reading this key
  localStorage.setItem('qs_token', token);

  window.location.href = options?.redirectTo || '/dashboard';
}
