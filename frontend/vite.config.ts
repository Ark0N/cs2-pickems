import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API base defaults to http://localhost:8000 (CORS is open in dev).
// Override with VITE_API_BASE if the backend runs elsewhere.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
