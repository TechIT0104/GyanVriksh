import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/shared/Layout";
import LandingTour from "./components/shared/LandingTour";
import { useAuth } from "./store/auth";
import { useTour } from "./store/tour";
import Admin from "./pages/Admin";
import AskCopilot from "./pages/AskCopilot";
import Compliance from "./pages/Compliance";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import GraphExplorer from "./pages/GraphExplorer";
import KnowledgeCliff from "./pages/KnowledgeCliff";
import EquipmentQR from "./pages/EquipmentQR";
import LessonsLearned from "./pages/LessonsLearned";
import Login from "./pages/Login";
import Maintenance from "./pages/Maintenance";
import MobileField from "./pages/MobileField";
import PreservationStudio from "./pages/PreservationStudio";

export default function App() {
  const token = useAuth((s) => s.token);
  const toured = useTour((s) => s.toured);
  if (!token) return <Login />;
  if (!toured) return <LandingTour />;
  return (
    <Routes>
      <Route path="/mobile" element={<MobileField />} />
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/ask" element={<AskCopilot />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/graph" element={<GraphExplorer />} />
        <Route path="/cliff" element={<KnowledgeCliff />} />
        <Route path="/qr" element={<EquipmentQR />} />
        <Route path="/compliance" element={<Compliance />} />
        <Route path="/maintenance" element={<Maintenance />} />
        <Route path="/preserve" element={<PreservationStudio />} />
        <Route path="/lessons" element={<LessonsLearned />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
