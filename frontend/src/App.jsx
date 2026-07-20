import { useEffect, useState } from "react";
import axios from "axios";

const apiRoot = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

function ServiceCard({ name, value }) {
  const healthy = value === true || value === "ok";
  return (
    <article className="card">
      <div className={`status ${healthy ? "healthy" : "pending"}`} />
      <div>
        <h3>{name}</h3>
        <p>{String(value)}</p>
      </div>
    </article>
  );
}

export default function App() {
  const [status, setStatus] = useState({ api: "loading", postgres: "loading", redis: "loading" });
  const [error, setError] = useState("");

  useEffect(() => {
    axios.get(`${apiRoot}/status/`)
      .then((response) => setStatus(response.data))
      .catch((requestError) => setError(requestError.message));
  }, []);

  return (
    <main className="shell">
      <section className="hero">
        <span className="eyebrow">FOUNDATION · PHASE 1</span>
        <h1>Startup Intelligence Platform</h1>
        <p>
          Upgradeable foundation for verified government schemes, loans,
          registrations, certificates, eligibility and grounded AI guidance.
        </p>
        <nav>
          <a href="http://localhost:8000/api/docs/" target="_blank">API docs</a>
          <a href="http://localhost:8000/admin/" target="_blank">Data admin</a>
          <a href="http://localhost:9001" target="_blank">Raw documents</a>
          <a href="http://localhost:6333/dashboard" target="_blank">Vector store</a>
        </nav>
      </section>

      {error && <div className="error">Backend connection error: {error}</div>}

      <section>
        <h2>Platform services</h2>
        <div className="grid">
          {Object.entries(status).map(([name, value]) => (
            <ServiceCard key={name} name={name} value={value} />
          ))}
        </div>
      </section>

      <section className="next">
        <h2>Next build modules</h2>
        <p>Source registry → raw document collector → extraction → verification → scheme publication.</p>
      </section>
    </main>
  );
}
