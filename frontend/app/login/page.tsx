'use client';

import { login } from '@/services/auth';

export default function LoginPage() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="bg-white p-8 rounded shadow w-96">
        <h1 className="text-xl font-bold mb-4">Sign in to FusionEMS Quantum</h1>
        <p className="text-sm text-gray-600 mb-4">You will be redirected to secure Cognito sign-in.</p>
        <button className="w-full bg-blue-600 text-white p-2 rounded" onClick={() => login()}>
          Continue
        </button>
      </div>
    </div>
  );
}
