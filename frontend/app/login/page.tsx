'use client';

import { useState } from 'react';
import { login } from '@/services/auth';

export default function LoginPage() {
  const [email, setEmail] = useState('');

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="bg-white p-8 rounded shadow w-96">
        <h1 className="text-xl font-bold mb-4">Login</h1>
        <input
          className="w-full border p-2 mb-4"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <button
          className="w-full bg-blue-600 text-white p-2 rounded"
          onClick={() => login(email)}
        >
          Sign In
        </button>
      </div>
    </div>
  );
}