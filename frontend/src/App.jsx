import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppLayout from "./components/layout/AppLayout";
import Dashboard from "./pages/Dashboard";
import JobsPage from "./pages/jobs/JobsPage";

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/"     element={<Dashboard />} />
          <Route path="/jobs" element={<JobsPage />}  />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}