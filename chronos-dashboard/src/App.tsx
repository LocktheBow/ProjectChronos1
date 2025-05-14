import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Search from "./pages/Search";
import Relationships from "./pages/Relationships";
import './theme.css';

/**
 * Top‑level router.
 *  • `/dashboard` shows the full Chronos UI
 *  • `/relationships` shows the corporate relationship graph
 *  • `/search` shows the entity search interface
 *  • any other route redirects to the dashboard
 */
export default function App() {
  return (
    <BrowserRouter>
      <div className="app-container w-full h-full">
        <Layout>
          <Routes>
            <Route index element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/relationships" element={<Relationships />} />
            <Route path="/search" element={<Search />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Layout>
      </div>
    </BrowserRouter>
  );
}
