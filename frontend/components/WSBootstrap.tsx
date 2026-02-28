'use client';

import { useEffect } from 'react';
import { useAuth } from '@/components/AuthProvider';
import { initWSClient } from '@/services/websocket';

export function WSBootstrap() {
  const { user } = useAuth();

  useEffect(() => {
    if (!user?.token) return;

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || `wss://${window.location.host}/ws`;
    initWSClient({ url: wsUrl, token: user.token });
  }, [user?.token]);

  return null;
}
