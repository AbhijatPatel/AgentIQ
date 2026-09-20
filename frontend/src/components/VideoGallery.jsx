import { useState, useEffect } from "react";
import { createPortal } from "react-dom";

export default function VideoGallery({ videos }) {
  const [selectedVideo, setSelectedVideo] = useState(null);

  useEffect(() => {
    if (!selectedVideo) return;

    // Lock body scroll when modal is open
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        setSelectedVideo(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [selectedVideo]);

  if (!videos || videos.length === 0) return null;

  const closePreview = () => {
    setSelectedVideo(null);
  };

  const isYouTube = (video) => video.source === "youtube" || video.embed_url;

  return (
    <div className="video-gallery">
      <div className="section-header-row">
        <div>
          <div className="section-kicker">Multimedia & Stream Intelligence</div>
          <h3 className="section-card-title">
            <span className="section-icon">🎬</span> Related Videos
            <span className="section-counter-badge">{videos.length}</span>
          </h3>
        </div>
      </div>

      <div className="video-grid">
        {videos.map((video, i) => (
          <button
            type="button"
            key={i}
            className="video-card"
            onClick={() => setSelectedVideo(video)}
            aria-label={`Watch ${video.title || "video"}`}
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

              <div className="video-play-overlay">
                <span className="video-play-button" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </span>
              </div>

              {/* Source badge */}
              {isYouTube(video) ? (
                <span className="video-source-badge video-source-badge--yt" aria-hidden="true">
                  YouTube
                </span>
              ) : (
                <span className="video-source-badge video-source-badge--pexel" aria-hidden="true">
                  Pexels
                </span>
              )}

              {/* Duration overlay */}
              {video.duration && (
                <span className="video-duration-badge" aria-hidden="true">
                  {video.duration}
                </span>
              )}
            </div>

            <div className="video-card-body">
              <div className="video-card-title" title={video.title}>
                {video.title}
              </div>

              {/* Channel & views for YouTube or author */}
              <div className="video-card-meta">
                {video.channel && <span className="video-channel">{video.channel}</span>}
                {video.views && <span className="video-views">· {video.views}</span>}
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Render modal directly into document.body using Portal so it's strictly viewport-centered */}
      {selectedVideo &&
        createPortal(
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
              aria-label={selectedVideo.title || "Video player"}
            >
              <div className="video-modal-header">
                <div className="video-modal-header-left">
                  {isYouTube(selectedVideo) && (
                    <span className="video-source-badge video-source-badge--yt">YouTube</span>
                  )}
                  <h4 className="video-modal-title" title={selectedVideo.title}>
                    {selectedVideo.title}
                  </h4>
                </div>

                <button
                  type="button"
                  onClick={closePreview}
                  className="video-close-button"
                  aria-label="Close video player"
                >
                  ✕
                </button>
              </div>

              <div className="video-modal-content">
                {/* YouTube videos use responsive iframe embed; Pexels use native <video> */}
                {isYouTube(selectedVideo) ? (
                  <div className="video-embed-container">
                    <iframe
                      src={`${selectedVideo.embed_url}?autoplay=1&rel=0`}
                      title={selectedVideo.title}
                      className="video-embed-iframe"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    />
                  </div>
                ) : (
                  <div className="video-player-container">
                    <video
                      controls
                      autoPlay
                      playsInline
                      poster={selectedVideo.thumbnail}
                      className="video-player"
                      src={selectedVideo.preview_video_url}
                    >
                      Your browser does not support video playback.
                    </video>
                  </div>
                )}
              </div>

              <div className="video-modal-footer">
                <div className="video-modal-footer-meta">
                  {selectedVideo.channel && (
                    <span className="video-modal-channel">
                      Channel: <strong>{selectedVideo.channel}</strong>
                    </span>
                  )}
                  {selectedVideo.views && (
                    <span className="video-modal-views"> · {selectedVideo.views}</span>
                  )}
                </div>

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
                  {isYouTube(selectedVideo) ? "Watch on YouTube ↗" : "Open Original Source ↗"}
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}