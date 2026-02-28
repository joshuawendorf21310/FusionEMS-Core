import './globals.css';
import { ReactNode } from 'react';
import { AuthProvider } from '@/components/AuthProvider';
import { WSBootstrap } from '@/components/WSBootstrap';

export const metadata = {
  title: 'FusionEMS Quantum',
  description: 'Enterprise EMS Revenue + Operations OS',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700;900&family=Barlow+Condensed:wght@400;500;600;700;900&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <AuthProvider>
          <WSBootstrap />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
