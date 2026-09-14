import SourceList from "./SourceList";

function Section({ title, content }) {
  if (!content) return null;
  return (
    <div style={{ marginBottom: "1.25rem" }}>
      <h3 style={{ fontSize: "1rem", marginBottom: "0.35rem" }}>{title}</h3>
      <p style={{ lineHeight: "1.6", color: "#374151", whiteSpace: "pre-wrap" }}>{content}</p>
    </div>
  );
}

export default function ReportViewer({ report, critique }) {
  if (!report) return null;

  return (
    <div
      style={{
        marginTop: "2rem",
        padding: "1.5rem",
        border: "1px solid #e5e7eb",
        borderRadius: "12px",
        background: "#ffffff",
      }}
    >
      <h2 style={{ marginBottom: "0.5rem" }}>{report.title}</h2>

      {critique && (
        <p style={{ color: "#6b7280", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Quality score: {critique.score}/10 · Status: {critique.status}
        </p>
      )}

      <Section title="Executive Summary" content={report.executive_summary} />
      <Section title="Introduction" content={report.introduction} />
      <Section title="Findings" content={report.findings} />
      <Section title="Analysis" content={report.analysis} />
      <Section title="Limitations" content={report.limitations} />
      <Section title="Conclusion" content={report.conclusion} />

      <SourceList references={report.references} />
    </div>
  );
}