import { useState } from "react";
import ReactMarkdown from "react-markdown";

export default function App() {
  const [topic, setTopic] = useState("");
  const [trace, setTrace] = useState([]);
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState(false);

  const runResearch = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setTrace([]);
    setReport("");

    const res = await fetch("http://localhost:8000/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      const lines = text.split("\n");

      for (const line of lines) {
        if (line.startsWith("event: trace")) continue;
        if (line.startsWith("event: report")) continue;
        if (line.startsWith("event: done")) {
          setLoading(false);
          break;
        }
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.report) setReport(data.report);
            else if (data.type) setTrace((prev) => [...prev, data]);
          } catch (_) {}
        }
      }
    }
    setLoading(false);
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
          onKeyDown={(e) => e.key === "Enter" && runResearch()}
          placeholder="e.g. Impact of AI on software engineering jobs in 2025"
          style={{
            flex: 1,
            padding: "10px 14px",
            borderRadius: 8,
            border: "1px solid #ddd",
            fontSize: 15,
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
            cursor: "pointer",
            fontSize: 15,
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "Researching…" : "Research →"}
        </button>
      </div>

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
              marginBottom: 10,
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
