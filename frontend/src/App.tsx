import { useState } from "react";
import { AnalyzerView } from "./components/AnalyzerView";
import { LandingPage } from "./components/LandingPage";

type View = "landing" | "app";

export default function App() {
  const [view, setView] = useState<View>("landing");
  return view === "landing" ? (
    <LandingPage onEnterApp={() => setView("app")} />
  ) : (
    <AnalyzerView onBack={() => setView("landing")} />
  );
}
