/*
 * Shared axios instance for REST calls: baseURL from env, 15s timeout.
 * UI code must go through travelService, never import this directly.
 * (Streaming uses fetch in stream.ts, not this instance.)
 */
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 15000
});

api.interceptors.response.use(
  (r) => r,
  (err) => Promise.reject(err)
);
