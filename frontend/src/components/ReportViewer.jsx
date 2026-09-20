import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SourceList from "./SourceList";

function Section({ title, content }) {
  if (!content) return null;
  return (
    <section className="report-section">
      <h3 className="report-section-subtitle">{title}</h3>
      <div className="markdown-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </section>
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
    const original = button.innerHTML;
    button.innerHTML = ok ? "✓ Copied!" : "Failed";
    setTimeout(() => {
      button.innerHTML = original;
    }, 1800);
  };

  return (
    <div className="report-viewer">
      <div className="report-heading">
        <div>
          <div className="section-kicker">Synthesized Research Output</div>
          <h2 className="report-title">{report.title}</h2>
        </div>
        <div className="report-actions">
          <button onClick={handleCopy} className="toolbar-btn" title="Copy markdown to clipboard">
            📋 Copy Report
          </button>
          <button onClick={() => downloadReport(report)} className="toolbar-btn" title="Download markdown file">
            📥 Download .md
          </button>
        </div>
      </div>

      {critique && (
        <div className="report-meta-row">
          <span className="report-meta-item">
            Quality Score: <strong>{critique.score}/10</strong>
          </span>
          <span className={`critique-status critique-${critique.status}`}>
            {critique.status === "pass" ? "✓ Verified Pass" : critique.status}
          </span>
          {report.references?.length > 0 && (
            <span className="report-meta-item">
              📚 <strong>{report.references.length}</strong> primary references
            </span>
          )}
        </div>
      )}

      <div className="report-body-container">
        <Section title="Executive Summary" content={report.executive_summary} />
        <Section title="Introduction" content={report.introduction} />
        <Section title="Key Findings & Evidence" content={report.findings} />
        <Section title="In-Depth Analysis" content={report.analysis} />
        <Section title="Limitations & Open Questions" content={report.limitations} />
        <Section title="Conclusion & Strategic Recommendations" content={report.conclusion} />
      </div>

      <SourceList references={report.references} />
    </div>
  );
}
