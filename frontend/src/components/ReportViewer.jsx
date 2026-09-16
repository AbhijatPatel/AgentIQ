import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SourceList from "./SourceList";

function Section({ title, content }) {
  if (!content) return null;
  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>{title}</h3>
      <div className="markdown-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

function buildPlainTextReport(report) {
  const sections = [
    `# ${report.title}`,
    "",
    "## Executive Summary",
    report.executive_summary,
    "",
    "## Introduction",
    report.introduction,
    "",
    "## Findings",
    report.findings,
    "",
    "## Analysis",
    report.analysis,
    "",
    "## Limitations",
    report.limitations,
    "",
    "## Conclusion",
    report.conclusion,
    "",
  ];

  if (report.references?.length) {
    sections.push("## References");
    report.references.forEach((ref) => {
      sections.push(`- ${ref.title}${ref.url ? ` (${ref.url})` : ""}`);
    });
  }

  return sections.join("\n");
}

async function copyReport(report) {
  const text = buildPlainTextReport(report);
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function downloadReport(report) {
  const text = buildPlainTextReport(report);
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${report.title.replace(/[^a-z0-9]+/gi, "_").toLowerCase()}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function ReportViewer({ report, critique }) {
  if (!report) return null;

  const handleCopy = async (e) => {
    const button = e.currentTarget;
    const ok = await copyReport(report);
    const original = button.textContent;
    button.textContent = ok ? "Copied!" : "Failed to copy";
    setTimeout(() => {
      button.textContent = original;
    }, 1500);
  };

    return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "1rem",
          marginBottom: "0.5rem",
        }}
      >
                <h2 style={{ margin: 0, fontSize: "1.5rem" }}>{report.title}</h2>
        <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0 }}>
                  <button onClick={handleCopy} className="toolbar-btn" style={toolbarButtonStyle}>
            Copy
          </button>
          <button onClick={() => downloadReport(report)} className="toolbar-btn" style={toolbarButtonStyle}>
            Download
          </button>
        </div>
      </div>

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

const toolbarButtonStyle = {
  padding: "0.4rem 0.9rem",
  borderRadius: "6px",
  border: "1px solid #d1d5db",
  background: "white",
  cursor: "pointer",
  fontSize: "0.85rem",
};

