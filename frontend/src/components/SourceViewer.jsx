import { useState } from "react";

function extractDomain(url) {
  if (!url) return null;

  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

function groupBySource(evidence) {
  const groups = {};

  for (const item of evidence) {
    const key = item.source_title || "Unknown source";

    if (!groups[key]) {
      groups[key] = {
        source_title: key,
        source_url: item.source_url,
        claims: [],
      };
    }

    groups[key].claims.push(item);
  }

  return Object.values(groups);
}

function SourceCard({ source, isExpanded, onToggle }) {
  const domain = extractDomain(source.source_url);

  const openSource = () => {
    if (source.source_url) {
      window.open(source.source_url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div className={`source-card ${isExpanded ? "source-card--expanded" : ""}`}>
      <button
        type="button"
        onClick={onToggle}
        className="source-card-toggle"
        aria-expanded={isExpanded}
      >
        <div className="source-info">
          <div className="source-title-row">
            <span className="source-bullet">🔗</span>
            <span className="source-title">{source.source_title}</span>
          </div>

          {domain && <div className="source-domain">{domain}</div>}
        </div>

        <div className="source-summary">
          <span className="source-claim-count">
            {source.claims.length} {source.claims.length === 1 ? "claim" : "claims"}
          </span>

          <span className={`source-chevron ${isExpanded ? "source-chevron--open" : ""}`}>
            ▾
          </span>
        </div>
      </button>

      {isExpanded && (
        <div className="source-card-body">
          {source.source_url ? (
            <button
              type="button"
              onClick={openSource}
              className="source-link"
            >
              Visit verified source ↗
            </button>
          ) : null}

          <ul className="source-claims">
            {source.claims.map((claim, i) => (
              <li key={i} className="source-claim-item">
                <span className="claim-text">{claim.claim}</span>
                <span className={`claim-tag claim-${claim.type || "evidence"}`}>
                  {claim.type || "fact"} {claim.confidence ? `· ${claim.confidence}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function SourceViewer({ evidence }) {
  if (!evidence || evidence.length === 0) return null;

  const sources = groupBySource(evidence);
  const [expandedMap, setExpandedMap] = useState({});
  const [expandAll, setExpandAll] = useState(false);

  const toggleSource = (index) => {
    setExpandedMap((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  const handleToggleAll = () => {
    const nextState = !expandAll;
    setExpandAll(nextState);
    const newMap = {};
    sources.forEach((_, i) => {
      newMap[i] = nextState;
    });
    setExpandedMap(newMap);
  };

  return (
    <div className="sources-viewer">
      <div className="section-header-row">
        <div>
          <div className="section-kicker">Citations & Verification</div>
          <h3 className="section-card-title">
            <span className="section-icon">📚</span> Sources & Extracted Claims
            <span className="section-counter-badge">
              {sources.length} sources · {evidence.length} claims
            </span>
          </h3>
        </div>

        <button
          type="button"
          onClick={handleToggleAll}
          className="toggle-all-btn"
        >
          {expandAll ? "Collapse all" : "Expand all"}
        </button>
      </div>

      <div className="source-cards-list">
        {sources.map((source, i) => (
          <SourceCard
            key={i}
            source={source}
            isExpanded={Boolean(expandedMap[i])}
            onToggle={() => toggleSource(i)}
          />
        ))}
      </div>
    </div>
  );
}