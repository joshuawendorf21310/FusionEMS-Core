'use client';

import { login } from '@/services/auth';

export default function LoginPage() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="bg-white p-8 rounded shadow w-96">
        <h1 className="text-xl font-bold mb-4">Sign in to FusionEMS Quantum</h1>
        <button className="w-full bg-blue-600 text-white p-2 rounded" onClick={() => login()}>
          Continue
        </button>
      </div>
    </div>
  );
}
