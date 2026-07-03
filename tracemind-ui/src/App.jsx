import { useState } from "react";
import TraceMindDashboard from "./components/TraceMindDashboard";
import TraceMindExplainer from "./components/TraceMindExplainer";

export default function App() {
  const [view, setView] = useState("dashboard");
  return (
    <div>
      <div className="flex gap-2 justify-center py-3 bg-slate-950">
        <button onClick={() => setView("dashboard")} className="text-xs text-slate-400 px-3 py-1">Dashboard</button>
        <button onClick={() => setView("explainer")} className="text-xs text-slate-400 px-3 py-1">How it works</button>
      </div>
      {view === "dashboard" ? <TraceMindDashboard /> : <TraceMindExplainer />}
    </div>
  );
}