"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const ACCENT = "#6366f1";

const AGENTS = [
  { key: "business", label: "Business Analyst", short: "BA", desc: "Market viability & business model" },
  { key: "developer", label: "Senior Developer", short: "Dev", desc: "Architecture & scalability" },
  { key: "qa", label: "QA Engineer", short: "QA", desc: "Testing strategy & edge cases" },
  { key: "security", label: "Security Engineer", short: "Sec", desc: "Vulnerabilities & compliance" },
  { key: "ux", label: "UX Researcher", short: "UX", desc: "Usability & retention" },
  { key: "orchestrator", label: "Final Specification", short: "SRS", desc: "Complete SRS synthesis" },
];

const KEY_MAP = {
  business: "business_analysis",
  developer: "dev_concerns",
  qa: "qa_concerns",
  security: "security_concerns",
  ux: "ux_concerns",
  orchestrator: "final_spec",
};

const VERDICTS = {
  promising: { bg: "#020f06", border: "#16a34a", color: "#4ade80", label: "Promising" },
  needs_clarification: { bg: "#0f0800", border: "#d97706", color: "#fbbf24", label: "Needs Clarification" },
  needs_work: { bg: "#0f0800", border: "#d97706", color: "#fbbf24", label: "Needs Work" },
  not_viable: { bg: "#0f0008", border: "#be123c", color: "#fb7185", label: "Not Viable" },
  risky: { bg: "#0f0008", border: "#be123c", color: "#fb7185", label: "Risky" },
  unclear: { bg: "#080810", border: "#334155", color: "#64748b", label: "Unclear" },
  feasible: { bg: "#020f06", border: "#16a34a", color: "#4ade80", label: "Feasible" },
  complex: { bg: "#0f0800", border: "#d97706", color: "#fbbf24", label: "Complex" },
  needs_review: { bg: "#0f0800", border: "#d97706", color: "#fbbf24", label: "Needs Review" },
  testable: { bg: "#020f06", border: "#16a34a", color: "#4ade80", label: "Testable" },
  secure: { bg: "#020f06", border: "#16a34a", color: "#4ade80", label: "Secure" },
  medium: { bg: "#04081a", border: "#3b82f6", color: "#60a5fa", label: "Medium" },
  high: { bg: "#020f06", border: "#16a34a", color: "#4ade80", label: "High" },
  low: { bg: "#0f0008", border: "#be123c", color: "#fb7185", label: "Low" },
};

function VerdictBadge({ verdict }) {
  const v = VERDICTS[verdict?.toLowerCase()] || VERDICTS.unclear;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "3px 10px", borderRadius: 999, fontWeight: 700,
      fontSize: 10, letterSpacing: "0.07em", textTransform: "uppercase",
      background: v.bg, border: `1px solid ${v.border}`, color: v.color,
    }}>
      <span style={{ width: 4, height: 4, borderRadius: "50%", background: v.color }} />
      {v.label}
    </span>
  );
}

function Section({ title, items }) {
  if (!items?.length) return null;
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{
        fontSize: 9, fontWeight: 700, color: "#475569",
        textTransform: "uppercase", letterSpacing: "0.14em",
        fontFamily: "monospace", marginBottom: 8,
        paddingBottom: 6, borderBottom: "1px solid #0f0f1c",
        display: "flex", alignItems: "center", gap: 8
      }}>
        {title}
        <span style={{
          fontSize: 9, padding: "1px 6px", borderRadius: 999,
          background: `${ACCENT}15`, border: `1px solid ${ACCENT}25`,
          color: `${ACCENT}90`, fontFamily: "monospace"
        }}>{items.length}</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {items.map((item, i) => (
          <div key={i} style={{
            display: "flex", gap: 10, padding: "9px 12px",
            background: "#060610", borderRadius: 7,
            border: "1px solid #0c0c1c",
            borderLeft: `2px solid ${ACCENT}25`,
            fontSize: 12, color: "#94a3b8", lineHeight: 1.6
          }}>
            <span style={{ color: `${ACCENT}50`, flexShrink: 0, fontSize: 8, marginTop: 3 }}>▸</span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TextField({ label, value }) {
  if (!value) return null;
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{
        fontSize: 9, fontWeight: 700, color: "#475569",
        textTransform: "uppercase", letterSpacing: "0.14em",
        fontFamily: "monospace", marginBottom: 6,
        paddingBottom: 6, borderBottom: "1px solid #0f0f1c"
      }}>{label}</div>
      <p style={{ fontSize: 12.5, color: "#94a3b8", lineHeight: 1.75, margin: 0 }}>{value}</p>
    </div>
  );
}

function AgentOutput({ data }) {
  if (!data) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 200, gap: 8, color: "#1e2035" }}>
      <span style={{ fontSize: 28 }}>◌</span>
      <span style={{ fontSize: 12 }}>Select an agent to view output</span>
    </div>
  );

  const verdict = data.verdict || data.project_viability;
  const scores = Object.entries(data).filter(([k, v]) => k.endsWith("_score") && typeof v === "number");
  const recommendation = data.recommendation || data.final_recommendation;
  const summary = data.product_summary || data.core_problem_statement;
  const lists = Object.entries(data).filter(([k, v]) => Array.isArray(v) && v.length && k !== "_meta");
  const textFields = Object.entries(data).filter(([k, v]) =>
    typeof v === "string" && !["role", "verdict", "project_viability", "recommendation",
      "final_recommendation", "product_summary", "core_problem_statement"].includes(k));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {(verdict || scores.length > 0) && (
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          flexWrap: "wrap", gap: 12, padding: "14px 16px",
          background: "#07070f", border: "1px solid #0f0f1c", borderRadius: 10
        }}>
          <div>
            {verdict && <VerdictBadge verdict={verdict} />}
          </div>
          {scores.length > 0 && (
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {scores.map(([k, v]) => (
                <div key={k} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: "50%",
                    background: "#0d0d1a",
                    border: `2px solid ${ACCENT}40`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 13, fontWeight: 700, color: ACCENT,
                    fontFamily: "monospace",
                  }}>{v}</div>
                  <span style={{
                    fontSize: 8, color: "#475569", textAlign: "center",
                    textTransform: "uppercase", letterSpacing: "0.1em",
                    fontFamily: "monospace", maxWidth: 54, lineHeight: 1.3
                  }}>{k.replace(/_score$/, "").replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {summary && (
        <div style={{
          padding: "13px 15px",
          background: `linear-gradient(135deg,${ACCENT}08,transparent)`,
          border: `1px solid ${ACCENT}18`, borderLeft: `3px solid ${ACCENT}`,
          borderRadius: 8, fontSize: 13, color: "#e2e8f0", lineHeight: 1.7
        }}>
          <div style={{
            fontSize: 9, fontWeight: 700, color: ACCENT,
            textTransform: "uppercase", letterSpacing: "0.12em",
            marginBottom: 7, fontFamily: "monospace"
          }}>
            {data.product_summary ? "Product Summary" : "Problem Statement"}
          </div>
          {summary}
        </div>
      )}

      {recommendation && (
        <div style={{
          padding: "13px 15px", background: "#07070f",
          border: "1px solid #0f0f1c", borderLeft: "3px solid #334155",
          borderRadius: 8, fontSize: 12.5, color: "#94a3b8", lineHeight: 1.75
        }}>
          <div style={{
            fontSize: 9, fontWeight: 700, color: "#64748b",
            textTransform: "uppercase", letterSpacing: "0.12em",
            marginBottom: 7, fontFamily: "monospace"
          }}>Recommendation</div>
          {recommendation}
        </div>
      )}

      {textFields.map(([k, v]) => (
        <TextField key={k} label={k.replace(/_/g, " ")} value={v} />
      ))}

      {lists.map(([k, v]) => (
        <Section key={k} title={k.replace(/_/g, " ")} items={v} />
      ))}
    </div>
  );
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function downloadReport(idea, results) {
  const lines = [];
  lines.push(`<html><head><meta charset="UTF-8"><style>
    body { font-family: Arial, sans-serif; max-width: 860px; margin: 40px auto; color: #1a1a1a; line-height: 1.6; }
    h1 { font-size: 22px; border-bottom: 2px solid #6366f1; padding-bottom: 10px; }
    h2 { font-size: 16px; margin-top: 32px; color: #1e1b4b; border-left: 4px solid #6366f1; padding-left: 10px; }
    h3 { font-size: 13px; margin-top: 20px; color: #374151; text-transform: uppercase; letter-spacing: 0.08em; }
    p { font-size: 13px; color: #374151; margin-bottom: 10px; }
    ul { margin: 0 0 12px; padding-left: 20px; }
    li { font-size: 13px; color: #374151; margin-bottom: 4px; }
    .agent-block { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 24px; }
    .rec-box { background: #f9fafb; border-left: 4px solid #9ca3af; padding: 12px 16px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; color: #4b5563; }
  </style></head><body>`);
  lines.push(`<h1>IdeaLens — Software Requirements Specification</h1>`);
  lines.push(`<p><strong>Idea:</strong> ${escapeHtml(idea)}<br><strong>Generated:</strong> ${new Date().toLocaleString()}</p>`);

  AGENTS.forEach(agent => {
    const data = results[agent.key];
    if (!data) return;
    const verdict = data.verdict || data.project_viability;
    const rec = data.recommendation || data.final_recommendation;
    const summary = data.product_summary || data.core_problem_statement;
    lines.push(`<div class="agent-block"><h2>${escapeHtml(agent.label)}</h2>`);
    if (verdict) lines.push(`<p><strong>Verdict:</strong> ${escapeHtml(verdict)}</p>`);
    if (summary) lines.push(`<p>${escapeHtml(summary)}</p>`);
    if (rec) lines.push(`<div class="rec-box"><strong>Recommendation:</strong><br>${escapeHtml(rec)}</div>`);
    Object.entries(data).forEach(([k, v]) => {
      if (Array.isArray(v) && v.length && k !== "_meta") {
        lines.push(`<h3>${escapeHtml(k.replace(/_/g, " "))} (${v.length})</h3><ul>`);
        v.forEach(item => lines.push(`<li>${escapeHtml(item)}</li>`));
        lines.push(`</ul>`);
      }
    });
    lines.push(`</div>`);
  });

  lines.push(`<div style="text-align:center;margin-top:40px">
    <button onclick="window.print()" style="padding:12px 32px;background:#6366f1;color:white;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer">
      ⬇ Save as PDF
    </button>
  </div></body></html>`);

  const blob = new Blob([lines.join("\n")], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "idialens-report.html";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [idea, setIdea] = useState("");
  const [phase, setPhase] = useState("idle");
  const [statuses, setStatuses] = useState({});
  const [results, setResults] = useState({});
  const [active, setActive] = useState(null);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [focused, setFocused] = useState(false);
  const [userApiKey, setUserApiKey] = useState("");
  const progressRef = useRef(null);

  const isIdle = phase === "idle";
  const isRunning = phase === "running";
  const isDone = phase === "done";
  const hasKey = userApiKey.trim().length > 0;
  const completedCount = Object.values(statuses).filter(s => s === "done").length;
  const currentAgent = AGENTS.find(a => statuses[a.key] === "running");

  useEffect(() => {
    let mounted = true;
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!mounted) return;
      if (!session) router.push("/login");
      else {
        setUser(session.user);
        setAuthChecked(true);
      }
    });
    return () => { mounted = false; };
  }, []);

  const startProgress = () => {
    setProgress(0);
    let p = 0;
    progressRef.current = setInterval(() => {
      p += 0.3;
      if (p >= 95) { clearInterval(progressRef.current); return; }
      setProgress(p);
    }, 400);
  };

  const stopProgress = () => {
    clearInterval(progressRef.current);
    setProgress(100);
    setTimeout(() => setProgress(0), 800);
  };

  const handleSubmit = async () => {
    if (!idea.trim() || isRunning) return;
    if (!hasKey) {
      setError("A Gemini API key is required. Paste yours below — get one free at https://aistudio.google.com/apikey");
      return;
    }
    setPhase("running");
    setResults({});
    setActive(null);
    setError(null);
    const init = {};
    AGENTS.forEach(a => init[a.key] = "waiting");
    setStatuses(init);
    setStatuses(prev => ({ ...prev, business: "running" }));
    startProgress();

    try {
      const res = await fetch(`${BACKEND}/generate-spec-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea, api_key: userApiKey.trim() }),
      });

      if (!res.ok) {
        let msg = `Server error: ${res.status}`;
        try {
          const body = await res.json();
          msg = body.error || (typeof body.detail === "string" ? body.detail : msg);
        } catch { /* non-JSON body */ }
        throw new Error(msg);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const json = line.replace("data: ", "").trim();
          if (!json) continue;

          try {
            const event = JSON.parse(json);

            if (event.type === "status") {
              setStatuses(prev => ({ ...prev, [event.agent]: "running" }));
            }

            if (event.type === "result") {
              setResults(prev => {
                const updated = { ...prev, [event.agent]: event.data };
                if (Object.keys(updated).length === 1) setActive(event.agent);
                return updated;
              });
              setStatuses(prev => ({ ...prev, [event.agent]: "done" }));
            }

            if (event.type === "done") {
              stopProgress();
              setPhase("done");
            }

          } catch (e) {
            // skip malformed events
          }
        }
      }

    } catch (err) {
      stopProgress();
      setError(err.message || "Something went wrong.");
      setPhase("idle");
      setStatuses({});
    }
  };

  const handleReset = () => {
    setPhase("idle");
    setIdea("");
    setResults({});
    setStatuses({});
    setActive(null);
    setError(null);
    setProgress(0);
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  if (!authChecked) {
    return <div style={{ minHeight: "100vh", background: "#05050f" }} />;
  }

  return (
    <>
      <style>{`
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #05050f; font-family: 'Inter', sans-serif; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #07070f; }
        ::-webkit-scrollbar-thumb { background: #1e1e2e; border-radius: 2px; }
        .agent-btn { width: 100%; text-align: left; background: transparent; border: none; cursor: pointer; padding: 10px 14px; transition: all 0.15s; border-left: 2px solid transparent; }
        .agent-btn:hover { background: #08081a; }
        .agent-btn.active { background: linear-gradient(90deg, ${ACCENT}10, transparent); border-left-color: ${ACCENT}; }
        textarea:focus { outline: none; }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes shimmer {
          0% { background-position: -200% center; }
          100% { background-position: 200% center; }
        }
        .shimmer {
          background: linear-gradient(90deg, #6366f1, #a78bfa, #818cf8, #6366f1);
          background-size: 200% auto;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          animation: shimmer 3s linear infinite;
        }
        .fade-in { animation: fadeIn 0.4s ease forwards; }
        @media (max-width: 640px) {
          .results-grid { grid-template-columns: 1fr !important; }
          .feature-grid { grid-template-columns: 1fr !important; }
        }
      `}</style>

      <div style={{ minHeight: "100vh", background: "#05050f", color: "white" }}>

        {/* Navbar */}
        <nav style={{
          position: "sticky", top: 0, zIndex: 50,
          background: "#07070f", borderBottom: "1px solid #0f0f1c",
        }}>
          <div style={{
            maxWidth: 1280, margin: "0 auto",
            padding: "0 24px",
            height: 52, display: "flex", alignItems: "center",
            justifyContent: "space-between"
          }}>
            {/* Logo */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 28, height: 28, borderRadius: 7,
                background: `linear-gradient(135deg, ${ACCENT}, #7c3aed)`,
                display: "flex", alignItems: "center", justifyContent: "center",
                boxShadow: `0 0 16px ${ACCENT}40`
              }}>
                <span style={{ fontSize: 14 }}>◈</span>
              </div>
              <span style={{ fontWeight: 800, fontSize: 15, letterSpacing: "-0.02em" }}>
                Idea<span style={{ color: ACCENT }}>Lens</span>
              </span>
            </div>

            {/* Center status */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {isRunning && currentAgent && (
                <div style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "4px 12px", background: "#0a0820",
                  border: `1px solid ${ACCENT}30`, borderRadius: 999
                }}>
                  <span style={{
                    width: 10, height: 10, borderRadius: "50%",
                    border: `2px solid ${ACCENT}40`, borderTopColor: ACCENT,
                    animation: "spin 0.7s linear infinite", display: "inline-block"
                  }} />
                  <span style={{ fontSize: 10, color: ACCENT, fontFamily: "monospace" }}>
                    {currentAgent.label} analysing
                  </span>
                </div>
              )}
              {isDone && (
                <div style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "4px 12px", background: "#020d07",
                  border: "1px solid #16a34a40", borderRadius: 999
                }}>
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#34d399" }} />
                  <span style={{ fontSize: 10, color: "#34d399", fontFamily: "monospace" }}>
                    {completedCount}/6 complete
                  </span>
                </div>
              )}
            </div>

            {/* Right: user + logout */}
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 11, color: "#334155", fontFamily: "monospace" }}>
                {user?.email?.split("@")[0]}
              </span>
              <button onClick={handleLogout} style={{
                padding: "5px 12px", borderRadius: 7,
                background: "transparent", color: "#475569",
                border: "1px solid #1a1a2e", cursor: "pointer",
                fontSize: 11, fontFamily: "Inter, sans-serif"
              }}>Sign out</button>
            </div>
          </div>

          {/* Progress bar */}
          {isRunning && (
            <div style={{ height: 2, background: "#0f0f1c", overflow: "hidden" }}>
              <div style={{
                height: "100%",
                background: `linear-gradient(90deg, #4338ca, ${ACCENT}, #34d399)`,
                width: `${progress}%`, transition: "width 0.4s linear",
                boxShadow: `0 0 8px ${ACCENT}60`
              }} />
            </div>
          )}
        </nav>

        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 24px" }}>

          {/* Hero — only shown when idle */}
          {isIdle && (
            <div style={{ paddingTop: 64, paddingBottom: 40, maxWidth: 600 }} className="fade-in">
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "5px 12px", background: "#07051a",
                border: `1px solid ${ACCENT}30`, borderRadius: 999, marginBottom: 20
              }}>
                <span style={{ display: "flex", gap: 3 }}>
                  {[1, 2, 3, 4, 5].map(i => (
                    <span key={i} style={{ width: 4, height: 4, borderRadius: "50%", background: ACCENT, opacity: 0.4 + i * 0.1 }} />
                  ))}
                </span>
                <span style={{ fontSize: 10, color: ACCENT, fontFamily: "monospace", letterSpacing: "0.08em" }}>
                  6 AI AGENTS · RAG-GROUNDED · SRS OUTPUT
                </span>
              </div>

              <h1 style={{ fontSize: "clamp(32px,5vw,58px)", fontWeight: 800, lineHeight: 1.08, letterSpacing: "-0.03em", marginBottom: 16 }}>
                Your idea,<br />
                <span className="shimmer">stress-tested</span><br />
                from every angle
              </h1>

              <p style={{ fontSize: 14, color: "#64748b", lineHeight: 1.7, maxWidth: 480 }}>
                Six AI specialists analyse your product idea and synthesize a complete Software Requirements Specification — with MVP scope, security analysis, and implementation priorities.
              </p>
            </div>
          )}

          {/* Input area */}
          <div style={{ paddingTop: isIdle ? 0 : 24, paddingBottom: 16, transition: "padding 0.4s ease" }}>
            <div style={{
              borderRadius: 12, padding: 1,
              background: focused ? `linear-gradient(135deg,${ACCENT},#7c3aed,${ACCENT})` : "#0f0f1c",
              transition: "background 0.3s",
              boxShadow: focused ? `0 0 28px ${ACCENT}18` : "none"
            }}>
              <div style={{ borderRadius: 11, background: "#08081a", overflow: "hidden" }}>
                <textarea
                  value={idea}
                  onChange={e => setIdea(e.target.value)}
                  onFocus={() => setFocused(true)}
                  onBlur={() => setFocused(false)}
                  placeholder="Describe your product idea..."
                  readOnly={isRunning}
                  rows={isIdle ? 4 : 2}
                  style={{
                    width: "100%", background: "transparent",
                    border: "none", resize: "none",
                    fontFamily: "Inter, sans-serif", fontSize: 14,
                    lineHeight: 1.7, color: isRunning ? "#475569" : "#e2e8f0",
                    caretColor: ACCENT, padding: "16px 18px",
                    cursor: isRunning ? "default" : "text",
                    transition: "color 0.3s"
                  }}
                />
                {isIdle && (
                  <div style={{
                    padding: "8px 16px", borderTop: "1px solid #0f0f1c",
                    display: "flex", justifyContent: "flex-end"
                  }}>
                    <span style={{ fontSize: 10, color: "#334155", fontFamily: "monospace" }}>
                      {idea.length > 0 ? `${idea.length} chars` : ""}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {isIdle && (
              <div style={{ marginTop: 12 }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontFamily: "monospace", color: hasKey ? "#4ade80" : "#94a3b8" }}>
                    {hasKey ? "● Gemini API key set" : "Gemini API key"}
                    <span style={{ color: "#f87171" }}> *</span>
                  </span>
                  <a
                    href="https://aistudio.google.com/apikey"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 10, color: ACCENT, whiteSpace: "nowrap", fontFamily: "monospace" }}
                  >
                    Get a free key ↗
                  </a>
                </div>
                <input
                  type="password"
                  value={userApiKey}
                  onChange={e => setUserApiKey(e.target.value)}
                  placeholder="AQ.Ab... (or older AIza... key)"
                  style={{
                    width: "100%", boxSizing: "border-box",
                    padding: "10px 14px", borderRadius: 8,
                    background: "#08081a",
                    border: `1px solid ${hasKey ? "#1a1a2e" : "#3f2530"}`,
                    color: "#e2e8f0", fontSize: 12, fontFamily: "monospace",
                    outline: "none"
                  }}
                />
                <p style={{ fontSize: 10, color: "#334155", marginTop: 6, lineHeight: 1.5 }}>
                  Required — each analysis makes 6 Gemini calls that run entirely on your key's own quota. Your key is sent only to Google for this request and is never stored.
                </p>
              </div>
            )}

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
            {isDone && (
              <button onClick={() => downloadReport(idea, results)} style={{
                padding: "8px 16px", background: "#04081a",
                border: "1px solid #1e3a5f", color: "#60a5fa",
                borderRadius: 8, cursor: "pointer", fontSize: 11,
                fontFamily: "Inter, sans-serif",
                display: "inline-flex", alignItems: "center", gap: 6
              }}>
                ↓ Download Report
              </button>
            )}
            {isDone ? (
              <button onClick={handleReset} style={{
                padding: "8px 20px", background: "transparent",
                border: `1px solid ${ACCENT}30`, color: ACCENT,
                borderRadius: 8, cursor: "pointer", fontSize: 11,
                fontFamily: "Inter, sans-serif"
              }}>
                New Analysis →
              </button>
            ) : (
              <button onClick={handleSubmit} disabled={isRunning || !idea.trim() || !hasKey} style={{
                padding: "8px 22px",
                background: (isRunning || !idea.trim() || !hasKey) ? "#0a0a14" : `linear-gradient(135deg,#4338ca,#6d28d9)`,
                border: "1px solid", borderColor: (isRunning || !idea.trim() || !hasKey) ? "#1a1a2e" : "#5b4dcc",
                borderRadius: 8, color: (isRunning || !idea.trim() || !hasKey) ? "#334155" : "#fff",
                fontSize: 12, fontWeight: 600, cursor: (isRunning || !idea.trim() || !hasKey) ? "not-allowed" : "pointer",
                fontFamily: "Inter, sans-serif", display: "inline-flex", alignItems: "center", gap: 8,
                boxShadow: (isRunning || !idea.trim() || !hasKey) ? "none" : `0 0 20px ${ACCENT}28`,
                transition: "all 0.2s"
              }}>
                {isRunning ? (
                  <>
                    <span style={{ width: 10, height: 10, borderRadius: "50%", border: `2px solid ${ACCENT}40`, borderTopColor: ACCENT, animation: "spin 0.7s linear infinite", display: "inline-block" }} />
                    Analysing...
                  </>
                ) : "Generate Spec →"}
              </button>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            marginBottom: 16, padding: "12px 16px",
            background: "#0f0008", border: "1px solid #7f1d1d",
            borderRadius: 10, display: "flex", gap: 10, alignItems: "flex-start"
          }}>
            <span style={{ color: "#f87171", fontSize: 14 }}>⚠</span>
            <span style={{ fontSize: 12, color: "#fca5a5", lineHeight: 1.5 }}>{error}</span>
            <button onClick={() => setError(null)} style={{ marginLeft: "auto", background: "none", border: "none", color: "#7f1d1d", cursor: "pointer", fontSize: 16 }}>×</button>
          </div>
        )}

        {/* Pipeline + Results */}
        {!isIdle && (
          <div className="fade-in">
            {/* Agent pipeline strip */}
            <div style={{
              marginBottom: 16, padding: "16px 20px",
              background: "#07070f", border: "1px solid #0f0f1c", borderRadius: 10
            }}>
              <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
                <span style={{ fontSize: 9, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: "0.14em", fontFamily: "monospace" }}>
                  Agent Pipeline
                </span>
                <div style={{ flex: 1, height: 1, background: "#0f0f1c", margin: "0 10px" }} />
                <span style={{ fontSize: 10, color: "#475569", fontFamily: "monospace" }}>{completedCount}/6</span>
              </div>
              <div style={{ display: "flex", alignItems: "center" }}>
                {AGENTS.map((agent, i) => {
                  const s = statuses[agent.key];
                  const isRun = s === "running";
                  const isDn = s === "done";
                  return (
                    <div key={agent.key} style={{ display: "flex", alignItems: "center", flex: 1, minWidth: 0 }}>
                      <button onClick={() => isDn && setActive(agent.key)} style={{
                        display: "flex", flexDirection: "column", alignItems: "center",
                        gap: 4, flex: 1, padding: "2px", border: "none",
                        background: "transparent", cursor: isDn ? "pointer" : "default"
                      }}>
                        <div style={{ position: "relative" }}>
                          {isRun && (
                            <div style={{
                              position: "absolute", inset: -4, borderRadius: "50%",
                              border: `1px solid ${ACCENT}30`,
                              animation: "pulseRing 2s ease infinite"
                            }} />
                          )}
                          <div style={{
                            width: 34, height: 34, borderRadius: "50%",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            background: isDn ? `${ACCENT}14` : isRun ? "#100c28" : "#07070f",
                            border: `2px solid ${isDn ? ACCENT : isRun ? ACCENT : "#1a1a2e"}`,
                            transition: "all 0.4s cubic-bezier(.22,1,.36,1)",
                            boxShadow: isDn ? `0 0 12px ${ACCENT}40` : isRun ? `0 0 10px ${ACCENT}30` : "none",
                          }}>
                            {isDn
                              ? <span style={{ color: ACCENT, fontSize: 12, fontWeight: 700 }}>✓</span>
                              : isRun
                                ? <span style={{ width: 6, height: 6, borderRadius: "50%", background: ACCENT, display: "block", animation: "pulseGlow 1s ease infinite" }} />
                                : <span style={{ color: "#1e2035", fontSize: 9, fontWeight: 600, fontFamily: "monospace" }}>{i + 1}</span>
                            }
                          </div>
                        </div>
                        <span style={{
                          fontSize: 8, fontWeight: 600, fontFamily: "monospace",
                          letterSpacing: "0.05em",
                          color: isDn ? ACCENT : isRun ? ACCENT : "#1e2035",
                          transition: "color 0.3s", whiteSpace: "nowrap"
                        }}>{agent.short}</span>
                      </button>
                      {i < AGENTS.length - 1 && (
                        <div style={{
                          flex: "0 0 12px", height: 1,
                          background: isDn ? `${ACCENT}40` : "#0f0f1c",
                          transition: "background 0.5s ease"
                        }} />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Sidebar + main panel */}
            {Object.keys(results).length > 0 && (
              <div className="results-grid" style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 12, marginBottom: 32 }}>
                {/* Sidebar */}
                <div style={{
                  background: "#07070f", border: "1px solid #0f0f1c",
                  borderRadius: 10, overflow: "hidden",
                  position: "sticky", top: 68, height: "fit-content"
                }}>
                  <div style={{
                    padding: "10px 14px", borderBottom: "1px solid #0f0f1c",
                    display: "flex", justifyContent: "space-between", alignItems: "center"
                  }}>
                    <span style={{ fontSize: 9, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: "0.14em", fontFamily: "monospace" }}>
                      Agents
                    </span>
                    <span style={{ fontSize: 10, color: "#475569", fontFamily: "monospace" }}>
                      {Object.keys(results).length}/{AGENTS.length}
                    </span>
                  </div>
                  {AGENTS.filter(a => results[a.key]).map(agent => {
                    const result = results[agent.key];
                    const verdict = result?.verdict || result?.project_viability;
                    const isActive = active === agent.key;
                    const vc = VERDICTS[verdict?.toLowerCase()] || VERDICTS.unclear;
                    return (
                      <button key={agent.key}
                        className={`agent-btn${isActive ? " active" : ""}`}
                        onClick={() => setActive(agent.key)}
                        style={{ borderLeftColor: isActive ? ACCENT : "transparent" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 4 }}>
                          <span style={{
                            width: 6, height: 6, borderRadius: "50%", background: ACCENT, flexShrink: 0,
                            boxShadow: isActive ? `0 0 8px ${ACCENT}` : "none", transition: "box-shadow 0.2s"
                          }} />
                          <span style={{ fontSize: 12, fontWeight: 500, color: isActive ? "#e2e8f0" : "#64748b", transition: "color 0.15s" }}>
                            {agent.label}
                          </span>
                        </div>
                        {verdict && (
                          <div style={{ marginLeft: 13 }}>
                            <span style={{
                              display: "inline-flex", alignItems: "center", gap: 4,
                              fontSize: 8, padding: "2px 8px", borderRadius: 999,
                              background: vc.bg, border: `1px solid ${vc.border}`,
                              color: vc.color, fontWeight: 700, letterSpacing: "0.08em",
                              textTransform: "uppercase"
                            }}>
                              <span style={{ width: 3, height: 3, borderRadius: "50%", background: vc.color }} />
                              {vc.label}
                            </span>
                          </div>
                        )}
                      </button>
                    );
                  })}
                </div>

                {/* Main output panel */}
                <div style={{
                  background: "#07070f", border: "1px solid #0f0f1c",
                  borderRadius: 10, overflow: "hidden", minHeight: 400
                }}>
                  {active ? (() => {
                    const agent = AGENTS.find(a => a.key === active);
                    if (!agent) return null;
                    return (
                      <>
                        <div style={{
                          padding: "14px 22px", borderBottom: "1px solid #0f0f1c",
                          background: `linear-gradient(135deg,${ACCENT}06,transparent 60%)`,
                          display: "flex", alignItems: "center", gap: 10
                        }}>
                          <div style={{
                            width: 32, height: 32, borderRadius: "50%",
                            background: `${ACCENT}10`, border: `1.5px solid ${ACCENT}30`,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            flexShrink: 0, boxShadow: `0 0 14px ${ACCENT}20`
                          }}>
                            <span style={{ width: 9, height: 9, borderRadius: "50%", background: ACCENT, boxShadow: `0 0 10px ${ACCENT}` }} />
                          </div>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: 13, color: "#f1f5f9" }}>{agent.label}</div>
                            <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>{agent.desc}</div>
                          </div>
                        </div>
                        <div style={{ padding: "22px 26px", maxHeight: 680, overflowY: "auto" }} className="fade-in">
                          <AgentOutput data={results[active]} />
                        </div>
                      </>
                    );
                  })() : (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 8, color: "#1e2035" }}>
                      <span style={{ fontSize: 24 }}>◌</span>
                      <span style={{ fontSize: 12 }}>Select an agent from the sidebar</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Done banner */}
            {isDone && (
              <div style={{
                marginBottom: 32, padding: "16px 22px",
                background: "linear-gradient(135deg,#020d07,#030f08)",
                border: "1px solid #16a34a25", borderRadius: 10,
                display: "flex", alignItems: "center", gap: 14,
                justifyContent: "space-between"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: "50%",
                    background: "#052e16", border: "1px solid #16a34a40",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    boxShadow: "0 0 14px rgba(52,211,153,.18)"
                  }}>
                    <span style={{ color: "#4ade80", fontSize: 13 }}>✓</span>
                  </div>
                  <div>
                    <p style={{ fontSize: 12, fontWeight: 600, color: "#4ade80" }}>Specification generated & saved</p>
                    <p style={{ fontSize: 10, color: "#4ade8050", marginTop: 2, fontFamily: "monospace" }}>All 6 agents completed successfully</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Feature cards — shown only when idle */}
        {isIdle && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10, paddingBottom: 60 }} className="fade-in feature-grid">
            {[
              { icon: "◈", title: "Multi-Agent Analysis", desc: "6 specialized agents each contribute a distinct perspective. Business, tech, QA, security, UX, and final spec — all synthesized.", tags: ["BA", "Dev", "QA", "Sec", "UX"] },
              { icon: "⬡", title: "RAG-Grounded", desc: "Agents retrieve from GDPR, OWASP, and SaaS architecture docs before responding — grounded in real standards, not just training data.", tags: ["GDPR", "OWASP", "SaaS"] },
              { icon: "◆", title: "Production SRS Output", desc: "The Orchestrator synthesizes into MVP scope, functional requirements, security requirements, and launch risks ready for your team.", tags: ["SRS", "MVP", "Risks"] },
            ].map((card, i) => (
              <div key={i} style={{ padding: "18px 20px", background: "#07070f", border: "1px solid #0f0f1c", borderRadius: 10 }}>
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 10 }}>
                  <span style={{ fontSize: 18, color: ACCENT, textShadow: `0 0 18px ${ACCENT}60` }}>{card.icon}</span>
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap", justifyContent: "flex-end" }}>
                    {card.tags.map(t => (
                      <span key={t} style={{
                        fontSize: 7, padding: "2px 6px", background: `${ACCENT}0d`,
                        border: `1px solid ${ACCENT}20`, color: ACCENT,
                        borderRadius: 4, fontFamily: "monospace", letterSpacing: "0.06em"
                      }}>{t}</span>
                    ))}
                  </div>
                </div>
                <div style={{ fontWeight: 700, fontSize: 13, color: "#e2e8f0", marginBottom: 8 }}>{card.title}</div>
                <div style={{ fontSize: 12, color: "#64748b", lineHeight: 1.65 }}>{card.desc}</div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div >
    </>
  );
}