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

function SourceCard({ source }) {
  const [expanded, setExpanded] = useState(false);
  const domain = extractDomain(source.source_url);

  const openSource = () => {
    if (source.source_url) {
      window.open(source.source_url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: "8px",
        marginBottom: "0.75rem",
        overflow: "hidden",
      }}
    >
      <button
        onClick={() => setExpanded((e) => !e)}
        style={{
          width: "100%",
          textAlign: "left",
          padding: "0.75rem 1rem",
          background: "#f9fafb",
          border: "none",
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ fontWeight: 600 }}>{source.source_title}</div>

          {domain && (
            <div
              style={{
                fontSize: "0.8rem",
                color: "#6b7280",
              }}
            >
              {domain}
            </div>
          )}
        </div>

        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
          }}
        >
          <span
            style={{
              fontSize: "0.8rem",
              color: "#6b7280",
            }}
          >
            {source.claims.length} claim
            {source.claims.length !== 1 ? "s" : ""}
          </span>

          <span>{expanded ? "-" : "+"}</span>
        </span>
      </button>

      {expanded && (
        <div
          style={{
            padding: "0.75rem 1rem",
            borderTop: "1px solid #e5e7eb",
          }}
        >
          {source.source_url ? (
            <button
              onClick={openSource}
              style={{
                fontSize: "0.85rem",
                display: "block",
                marginBottom: "0.5rem",
                background: "none",
                border: "none",
                color: "#2563eb",
                cursor: "pointer",
                padding: 0,
                textDecoration: "underline",
              }}
            >
              View original source
            </button>
          ) : null}

          <ul
            style={{
              paddingLeft: "1.1rem",
              margin: 0,
            }}
          >
            {source.claims.map((claim, i) => (
              <li
                key={i}
                style={{
                  marginBottom: "0.5rem",
                  fontSize: "0.9rem",
                }}
              >
                {claim.claim}

                <span
                  style={{
                    marginLeft: "0.5rem",
                    fontSize: "0.7rem",
                    padding: "0.1rem 0.4rem",
                    borderRadius: "4px",
                    background:
                      claim.type === "evidence"
                        ? "#dcfce7"
                        : "#fef3c7",
                    color:
                      claim.type === "evidence"
                        ? "#166534"
                        : "#92400e",
                  }}
                >
                  {claim.type} - {claim.confidence}
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

  return (
    <div style={{ marginTop: "2rem" }}>
      <h3 style={{ marginBottom: "0.75rem" }}>
        Sources and Evidence ({sources.length} sources, {evidence.length}{" "}
        claims)
      </h3>

      {sources.map((source, i) => (
        <SourceCard key={i} source={source} />
      ))}
    </div>
  );
}