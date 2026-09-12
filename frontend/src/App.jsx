import { useState } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  const checkHealth = async () => {
    setError(null);
    setStatus(null);
    try {
      const res = await fetch("http://localhost:8000/api/health");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStatus(data.status);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>AgentIQ</h1>
      <p>Module 1 — Frontend to Backend connectivity test</p>
      <button onClick={checkHealth}>Check Backend Health</button>

      {status && <p style={{ color: "green" }}>Backend status: {status}</p>}
      {error && <p style={{ color: "red" }}>Error: {error}</p>}
    </div>
  );
}

export default App;