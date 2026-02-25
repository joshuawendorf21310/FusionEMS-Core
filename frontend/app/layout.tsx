import "./globals.css";
import React from "react";
import AppShell from "../components/AppShell";

export const metadata = {
  title: "FusionEMS Quantum",
  description: "Billing-first public safety operating system"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
