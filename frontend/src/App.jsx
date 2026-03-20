// src/App.jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import AppLayout       from "./components/layout/AppLayout";
import Dashboard       from "./pages/Dashboard";
import JobsPage        from "./pages/jobs/JobsPage";
import InterviewsPage  from "./pages/interviews/InterviewsPage";
import InterviewDetail from "./pages/interviews/InterviewDetail";

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/"                element={<Dashboard />}       />
          <Route path="/jobs"            element={<JobsPage />}        />
          <Route path="/interviews"      element={<InterviewsPage />}  />
          <Route path="/interviews/:id"  element={<InterviewDetail />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}