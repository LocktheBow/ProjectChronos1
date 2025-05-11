import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Link } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Search from "./pages/Search";

/**
 * Top‑level router.
 *  • `/dashboard` shows the full Chronos UI
 *  • any other route redirects to the dashboard
 */
export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow">
          <div className="mx-auto max-w-6xl px-4 py-3 flex gap-6">
            <Link to="/dashboard" className="font-medium hover:text-indigo-600">Dashboard</Link>
            <Link to="/search" className="font-medium hover:text-indigo-600">Search</Link>
          </div>
        </header>
        <Routes>
          <Route index element={<Search />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/search" element={<Search />} />
          <Route path="*" element={<Navigate to="/search" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
