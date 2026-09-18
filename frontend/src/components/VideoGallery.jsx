import { useState } from "react";

export default function VideoGallery({ videos }) {
  const [selectedVideo, setSelectedVideo] = useState(null);

  if (!videos || videos.length === 0) return null;

  const closePreview = () => {
    setSelectedVideo(null);
  };

  return (
    <div>
      <h3 style={{ marginBottom: "0.75rem" }}>
        🎥 Related Videos ({videos.length})
      </h3>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: "0.9rem",
        }}
      >
        {videos.map((video, i) => (
          <div
            key={i}
            onClick={() => setSelectedVideo(video)}
            style={{
              display: "block",
              borderRadius: "10px",
              overflow: "hidden",
              border: "1px solid var(--border)",
              cursor: "pointer",
              background: "#000",
              position: "relative",
            }}
          >
            <div style={{ position: "relative" }}>
              <img
                src={video.thumbnail}
                alt={video.title || "Video thumbnail"}
                loading="lazy"
                style={{
                  width: "100%",
                  height: "120px",
                  objectFit: "cover",
                  display: "block",
                  opacity: 0.9,
                }}
                onError={(e) => {
                  e.currentTarget.parentElement.parentElement.style.display =
                    "none";
                }}
              />

              <div
                style={{
                  position: "absolute",
                  top: "50%",
                  left: "50%",
                  transform: "translate(-50%, -50%)",
                  width: "42px",
                  height: "42px",
                  borderRadius: "50%",
                  background: "rgba(0,0,0,0.55)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                  fontSize: "1.1rem",
                }}
              >
                ▶
              </div>
            </div>

            <div
              style={{
                padding: "0.5rem 0.6rem",
                fontSize: "0.78rem",
                color: "var(--text-muted)",
                background: "var(--bg-subtle)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {video.title}
            </div>
          </div>
        ))}
      </div>

      {selectedVideo && (
        <div
          onClick={closePreview}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
            zIndex: 9999,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: "min(900px, 100%)",
              background: "#111827",
              borderRadius: "12px",
              overflow: "hidden",
              boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "0.75rem 1rem",
                color: "#fff",
              }}
            >
              <div
                style={{
                  fontWeight: 600,
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  paddingRight: "1rem",
                }}
              >
                {selectedVideo.title}
              </div>

              <button
                onClick={closePreview}
                style={{
                  border: "none",
                  background: "transparent",
                  color: "#fff",
                  fontSize: "1.5rem",
                  cursor: "pointer",
                }}
                aria-label="Close video preview"
              >
                ×
              </button>
            </div>

            <video
            controls
            playsInline
            preload="metadata"
              poster={selectedVideo.thumbnail}
              style={{
                width: "100%",
                maxHeight: "70vh",
                display: "block",
                background: "#000",
              }}
              src={selectedVideo.preview_video_url}
            >
              Your browser does not support video playback.
            </video>

            <div
              style={{
                padding: "0.75rem 1rem",
                display: "flex",
                justifyContent: "flex-end",
              }}
            >
              <button
                onClick={() =>
                  window.open(
                    selectedVideo.url,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
                style={{
                  padding: "0.5rem 0.8rem",
                  borderRadius: "6px",
                  border: "1px solid #374151",
                  background: "#1f2937",
                  color: "#fff",
                  cursor: "pointer",
                }}
              >
                Open Original ↗
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}