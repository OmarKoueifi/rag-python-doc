import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import ChatPage from "./pages/Chat";

// Keep recharts + admin widgets out of the chat page's initial bundle.
const AdminLoginPage = lazy(() => import("./pages/AdminLogin"));
const AdminDashboardPage = lazy(() => import("./pages/AdminDashboard"));

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route
        path="/admin/login"
        element={
          <Suspense fallback={<RouteFallback />}>
            <AdminLoginPage />
          </Suspense>
        }
      />
      <Route
        path="/admin"
        element={
          <Suspense fallback={<RouteFallback />}>
            <AdminDashboardPage />
          </Suspense>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function RouteFallback() {
  return (
    <div className="min-h-full flex items-center justify-center text-ink-400">
      Loading…
    </div>
  );
}
