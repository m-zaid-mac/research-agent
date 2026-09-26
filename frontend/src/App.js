import { useState } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

export default function App() {
  const [topic, setTopic] = useState("");
  const [trace, setTrace] = useState([]);
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runResearch = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setTrace([]);
    setReport("");
    setError("");

    try {
      const res = await fetch(`${API_BASE}/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });

      if (!res.ok) throw new Error(`Server returned ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let eventName = "message";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // stream:true keeps partial multi-byte characters intact across reads
        buffer += decoder.decode(value, { stream: true });

        // Only process whole lines. Anything after the last newline stays in
        // the buffer until the next read completes it.
        let nl;
        while ((nl = buffer.indexOf("\n")) !== -1) {
          const line = buffer.slice(0, nl).replace(/\r$/, "");
          buffer = buffer.slice(nl + 1);

          if (line.startsWith(":")) continue; // keep-alive ping
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
            continue;
          }
          if (!line.startsWith("data:")) continue;

          let payload;
          try {
            payload = JSON.parse(line.slice(5).trim());
          } catch {
            continue;
          }

          if (eventName === "trace") setTrace((prev) => [...prev, payload]);
          else if (eventName === "report") setReport(payload.report);
          else if (eventName === "error") setError(payload.message);
        }
      }
    } catch (e) {
      setError(e.message || "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const iconFor = (type) =>
    ({ decompose: "🧠", search: "🔍", synthesize: "✍️" })[type] || "⚙️";

  return (
    <div
      style={{
        maxWidth: 800,
        margin: "0 auto",
        padding: "2rem",
        fontFamily: "system-ui",
      }}
    >
      <h1 style={{ fontSize: 28, fontWeight: 600, marginBottom: 8 }}>
        AI Research Agent
      </h1>
      <p style={{ color: "#666", marginBottom: 24 }}>
        Enter a topic. The agent will search the web and synthesize a report.
      </p>

      <div style={{ display: "flex", gap: 10, marginBottom: 32 }}>
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !loading && runResearch()}
          placeholder="e.g. Impact of AI on software engineering jobs in 2025"
          disabled={loading}
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid #ddd",
            fontSize: 15,
            opacity: loading ? 0.6 : 1,
            cursor: loading ? "not-allowed" : "text",
          }}
        />
        <button
          onClick={runResearch}
          disabled={loading || !topic.trim()}
          style={{
            padding: "10px 22px",
            background: "#5B4FCF",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            cursor: loading || !topic.trim() ? "not-allowed" : "pointer",
            fontSize: 15,
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Researching…" : "Research →"}
        </button>
      </div>

      {error && (
        <div
          style={{
            background: "#fdf0f0",
            border: "1px solid #f3c9c9",
            borderRadius: 10,
            padding: 14,
            marginBottom: 20,
            color: "#912626",
            fontSize: 14,
          }}
        >
          {error}
        </div>
      )}

      {trace.length > 0 && (
        <div
          style={{
            background: "#f8f8f8",
            borderRadius: 10,
            padding: 16,
            marginBottom: 24,
          }}
        >
          <p
            style={{
              fontWeight: 600,
              fontSize: 13,
              color: "#888",
              textTransform: "uppercase",
              letterSpacing: 1,
              margin: "0 0 10px",
            }}
          >
            Agent trace
          </p>
          {trace.map((t, i) => (
            <div
              key={i}
              style={{
                display: "flex",
                gap: 8,
                alignItems: "flex-start",
                marginBottom: 6,
              }}
            >
              <span>{iconFor(t.type)}</span>
              <span style={{ fontSize: 14, color: "#444" }}>{t.content}</span>
            </div>
          ))}
          {loading && (
            <div style={{ fontSize: 13, color: "#888", marginTop: 8 }}>
              ⏳ Working…
            </div>
          )}
        </div>
      )}

      {report && (
        <div
          style={{
            background: "#fff",
            border: "1px solid #e5e5e5",
            borderRadius: 10,
            padding: 24,
          }}
        >
          <ReactMarkdown>{report}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
