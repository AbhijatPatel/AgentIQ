import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import SourceList from "./SourceList";

function cleanTitle(title) {
  if (!title) return "";
  return title.replace(/^(?:#+\s*)?(?:(?:\d+(?:\.\d+)*[\.\)\:\-]\s*)+|[IVXLCDM]+[\.\)\:\-]\s+|[\*\-\•]\s+)/i, "").trim();
}

function Section({ number, title, content }) {
  if (!content) return null;
  const semanticTitle = cleanTitle(title);
  const displayTitle = number ? `${number}. ${semanticTitle}` : semanticTitle;

  return (
    <section className="report-section">
      <h3 className="report-section-subtitle">{displayTitle}</h3>
      <div className="markdown-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    </section>
  );
}

function buildPlainTextReport(report) {
  const cleanMainTitle = cleanTitle(report.title);
  const sections = [
    `# ${cleanMainTitle}`,
    "",
    "## 1. Executive Summary",
    report.executive_summary,
    "",
    "## 2. Introduction",
    report.introduction,
    "",
    "## 3. Key Findings & Evidence",
    report.findings,
    "",
    "## 4. In-Depth Analysis",
    report.analysis,
    "",
    "## 5. Limitations & Open Questions",
    report.limitations,
    "",
    "## 6. Strategic Conclusion",
    report.conclusion,
    "",
  ];

  if (report.references?.length) {
    sections.push("## 7. References & Citations");
    report.references.forEach((ref, idx) => {
      sections.push(`[${idx + 1}] ${ref.title}${ref.url ? ` - ${ref.url}` : ""}`);
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
  const safeTitle = (cleanTitle(report.title) || "research_report").replace(/[^a-z0-9]+/gi, "_").toLowerCase();
  a.download = `${safeTitle}.md`;
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
          <h2 className="report-title">{cleanTitle(report.title)}</h2>
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
        <Section number={1} title="Executive Summary" content={report.executive_summary} />
        <Section number={2} title="Introduction" content={report.introduction} />
        <Section number={3} title="Key Findings & Evidence" content={report.findings} />
        <Section number={4} title="In-Depth Analysis" content={report.analysis} />
        <Section number={5} title="Limitations & Open Questions" content={report.limitations} />
        <Section number={6} title="Strategic Conclusion" content={report.conclusion} />
      </div>

      <SourceList references={report.references} />
    </div>
  );
}
