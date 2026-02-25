'use client';

import { useEffect, useState } from 'react';
import { getExecutiveSummary } from '@/services/api';

export default function Dashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    getExecutiveSummary().then(setData);
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Founder Dashboard</h1>
      {data && (
        <div className="grid grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded shadow">
            <h2 className="font-semibold">MRR</h2>
            <p>${data.mrr}</p>
          </div>
          <div className="bg-white p-6 rounded shadow">
            <h2 className="font-semibold">Clients</h2>
            <p>{data.clients}</p>
          </div>
          <div className="bg-white p-6 rounded shadow">
            <h2 className="font-semibold">System</h2>
            <p>{data.system_status}</p>
          </div>
        </div>
      )}
    </div>
  );
}