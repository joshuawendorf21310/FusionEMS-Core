let accessTokenMemory: string | null = null;

const cognitoDomain = process.env.NEXT_PUBLIC_COGNITO_DOMAIN || '';
const cognitoClientId = process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || '';
const redirectUri = process.env.NEXT_PUBLIC_COGNITO_REDIRECT_URI || 'https://fusionemsquantum.com/auth/callback';

export function login(): void {
  if (cognitoDomain && cognitoClientId) {
    const url = new URL(`https://${cognitoDomain}/login`);
    url.searchParams.set('response_type', 'token');
    url.searchParams.set('client_id', cognitoClientId);
    url.searchParams.set('redirect_uri', redirectUri);
    window.location.href = url.toString();
    return;
  }
  window.location.href = '/dashboard';
}

export function handleAuthCallbackHash(hash: string): string | null {
  const fragment = hash.startsWith('#') ? hash.slice(1) : hash;
  const params = new URLSearchParams(fragment);
  const token = params.get('access_token');
  if (!token) return null;
  accessTokenMemory = token;
  return token;
}

export function getAccessToken(): string | null {
  return accessTokenMemory;
}

export function logout(): void {
  accessTokenMemory = null;
  window.location.href = '/login';
}
