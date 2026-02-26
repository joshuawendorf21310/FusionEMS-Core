import axios from 'axios';
import { getAccessToken } from './auth';

const API = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

API.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function getExecutiveSummary() {
  const res = await API.get('/api/founder/executive-summary', {
    headers: { 'X-Tenant-ID': 'founder' },
  });
  return res.data;
}
