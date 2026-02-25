export function login(email: string) {
  // In production redirect to Cognito Hosted UI
  localStorage.setItem('token', 'demo-token');
  window.location.href = '/dashboard';
}