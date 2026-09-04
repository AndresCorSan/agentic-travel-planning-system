import axios from 'axios';

// Clean API layer. Not calling a backend yet — baseURL is read from env
// so future FastAPI integration only changes travelService internals.
// Kept intentionally: UI code must go through travelService, which will
// switch its bodies to `api.get/post(...)` without signature changes.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 15000
});

api.interceptors.response.use(
  (r) => r,
  (err) => Promise.reject(err)
);
