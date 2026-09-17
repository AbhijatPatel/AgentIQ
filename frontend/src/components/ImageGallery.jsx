export default function ImageGallery({ images }) {
  if (!images || images.length === 0) return null;

  const openImage = (url) => {
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div>
      <h3 style={{ marginBottom: "0.75rem" }}>🖼️ Related Images ({images.length})</h3>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
          gap: "0.75rem",
        }}
      >
        {images.map((img, i) => (
          <div
            key={i}
            onClick={() => openImage(img.url)}
            style={{
              display: "block",
              borderRadius: "10px",
              overflow: "hidden",
              border: "1px solid var(--border)",
              cursor: "pointer",
            }}
          >
            <img
              src={img.url}
              alt={img.description || "Research image"}
              loading="lazy"
              style={{
                width: "100%",
                height: "110px",
                objectFit: "cover",
                display: "block",
              }}
              onError={(e) => {
                e.currentTarget.parentElement.style.display = "none";
              }}
            />
            {img.description && (
              <div
                style={{
                  padding: "0.4rem 0.6rem",
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                  background: "var(--bg-subtle)",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {img.description}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}