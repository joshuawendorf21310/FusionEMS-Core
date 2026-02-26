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
      setError('Authentication callback did not include an access token.');
      return;
    }
    router.replace('/dashboard');
  }, [router]);

  return <div className="min-h-screen flex items-center justify-center">{error ?? 'Signing you in…'}</div>;
}
