import axios from 'axios';

const API = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL
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