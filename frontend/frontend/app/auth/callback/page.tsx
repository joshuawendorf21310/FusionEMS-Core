'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { handleAuthCallbackHash } from '@/services/auth';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = handleAuthCallbackHash(window.location.hash);
    if (!token) {
      setError('Missing access token in callback.');
      return;
    }
    router.replace('/dashboard');
  }, [router]);

  return <div className="min-h-screen flex items-center justify-center">{error ?? 'Signing you in…'}</div>;
}
