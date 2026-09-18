import { useState } from "react";

export default function VideoGallery({ videos }) {
  const [selectedVideo, setSelectedVideo] = useState(null);

  if (!videos || videos.length === 0) return null;

  const closePreview = () => {
    setSelectedVideo(null);
  };

  return (
    <div className="video-gallery">
      <h3 className="media-gallery-title">
        🎥 Related Videos ({videos.length})
      </h3>

      <div className="video-grid">
        {videos.map((video, i) => (
          <button
            type="button"
            key={i}
            className="video-card"
            onClick={() => setSelectedVideo(video)}
            aria-label={`Preview ${video.title || "research video"}`}
          >
            <div className="video-thumbnail-wrapper">
              <img
                src={video.thumbnail}
                alt={video.title || "Video thumbnail"}
                loading="lazy"
                className="video-thumbnail"
                onError={(e) => {
                  e.currentTarget.closest(".video-card").style.display = "none";
                }}
              />

              <span className="video-play-button" aria-hidden="true">
                ▶
              </span>
            </div>

            <div className="video-card-title">
              {video.title}
            </div>
          </button>
        ))}
      </div>

      {selectedVideo && (
        <div
          className="video-modal-backdrop"
          onClick={closePreview}
          role="presentation"
        >
          <div
            className="video-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label={selectedVideo.title || "Video preview"}
          >
            <div className="video-modal-header">
              <div className="video-modal-title">
                {selectedVideo.title}
              </div>

              <button
                type="button"
                onClick={closePreview}
                className="video-close-button"
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
              className="video-player"
              src={selectedVideo.preview_video_url}
            >
              Your browser does not support video playback.
            </video>

            <div className="video-modal-footer">
              <button
                type="button"
                onClick={() =>
                  window.open(
                    selectedVideo.url,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
                className="video-original-button"
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