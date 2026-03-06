import axios from 'axios';

export const API = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "",
});

export async function getExecutiveSummary() {
  const res = await API.get('/api/founder/executive-summary', {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Tenant-ID': 'founder'
    }
  });
  return res.data;
}