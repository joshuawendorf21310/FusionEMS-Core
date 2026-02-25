import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import './styles.css'

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">FusionEMS Quantum</div>
        <nav className="nav">
          <Link to="/">Landing</Link>
          <Link to="/cad">CAD</Link>
          <Link to="/mdt">MDT</Link>
          <Link to="/crewlink">CrewLink</Link>
          <Link to="/transportlink">TransportLink</Link>
          <Link to="/founder">Founder</Link>
        </nav>
      </header>
      <main className="main">{children}</main>
    </div>
  )
}

function Landing() {
  return (
    <Shell>
      <h1>FusionEMS Quantum</h1>
      <p>Unified Public Safety OS — Billing-first. Certification-gated modules.</p>
      <p>Use the navigation for CAD/MDT/CrewLink/TransportLink/Founder.</p>
    </Shell>
  )
}

function SimplePage({ title }: { title: string }) {
  return (
    <Shell>
      <h2>{title}</h2>
      <p>Offline-first PWA scaffold. Connects to realtime topics via backend.</p>
    </Shell>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/cad" element={<SimplePage title="CAD Console (2-screen ops supported via /cad/ops/board)" />} />
        <Route path="/mdt" element={<SimplePage title="MDT PWA" />} />
        <Route path="/crewlink" element={<SimplePage title="CrewLink PWA" />} />
        <Route path="/transportlink" element={<SimplePage title="TransportLink PWA" />} />
        <Route path="/founder" element={<SimplePage title="Founder Command Center" />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
