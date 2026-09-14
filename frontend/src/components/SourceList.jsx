export default function SourceList({ references }) {
  if (!references || references.length === 0) {
    return null;
  }

  return (
    <div style={{ marginTop: "1.5rem" }}>
      <h3 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>Sources</h3>
      <ul style={{ paddingLeft: "1.25rem" }}>
        {references.map((ref, i) => (
          <li key={i} style={{ marginBottom: "0.35rem" }}>
            {ref.url ? (
              <a href={ref.url} target="_blank" rel="noopener noreferrer">
                {ref.title}
              </a>
            ) : (
              <span>{ref.title}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}