import { useState, useEffect } from "react";
import { createPortal } from "react-dom";

export default function ImageGallery({ images }) {
  const [selectedImage, setSelectedImage] = useState(null);

  useEffect(() => {
    if (!selectedImage) return;

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        setSelectedImage(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [selectedImage]);

  if (!images || images.length === 0) return null;

  return (
    <div className="image-gallery">
      <div className="section-header-row">
        <div>
          <div className="section-kicker">Visual Evidence & Infographics</div>
          <h3 className="section-card-title">
            <span className="section-icon">🖼️</span> Related Images
            <span className="section-counter-badge">{images.length}</span>
          </h3>
        </div>
      </div>

      <div className="image-grid">
        {images.map((img, i) => (
          <button
            type="button"
            key={i}
            className="image-card"
            onClick={() => setSelectedImage(img)}
            aria-label={`Preview ${img.description || "research image"}`}
          >
            <div className="image-wrapper">
              <img
                src={img.url}
                alt={img.description || "Research image"}
                loading="lazy"
                className="image-card-preview"
                onError={(e) => {
                  e.currentTarget.closest(".image-card").style.display = "none";
                }}
              />
              <div className="image-zoom-indicator">
                <span>🔍 Zoom</span>
              </div>
            </div>

            {img.description && (
              <div className="image-card-description" title={img.description}>
                {img.description}
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Lightbox Preview Modal */}
      {selectedImage &&
        createPortal(
          <div
            className="image-modal-backdrop"
            onClick={() => setSelectedImage(null)}
            role="presentation"
          >
            <div
              className="image-modal"
              onClick={(e) => e.stopPropagation()}
              role="dialog"
              aria-modal="true"
              aria-label="Image preview"
            >
              <div className="image-modal-header">
                <span className="image-modal-title">
                  {selectedImage.description || "Image Preview"}
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedImage(null)}
                  className="video-close-button"
                  aria-label="Close preview"
                >
                  ✕
                </button>
              </div>

              <div className="image-modal-body">
                <img
                  src={selectedImage.url}
                  alt={selectedImage.description || "Preview"}
                  className="image-modal-full"
                />
              </div>

              <div className="image-modal-footer">
                <button
                  type="button"
                  onClick={() =>
                    window.open(
                      selectedImage.url,
                      "_blank",
                      "noopener,noreferrer"
                    )
                  }
                  className="secondary-btn"
                >
                  Open Full Resolution ↗
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </div>
  );
}