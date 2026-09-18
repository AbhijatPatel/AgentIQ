export default function ImageGallery({ images }) {
  if (!images || images.length === 0) return null;

  const openImage = (url) => {
    window.open(url, "_blank", "noopener,noreferrer");
  };

  return (
    <div className="image-gallery">
      <h3 className="media-gallery-title">
        🖼️ Related Images ({images.length})
      </h3>

      <div className="image-grid">
        {images.map((img, i) => (
          <button
            type="button"
            key={i}
            className="image-card"
            onClick={() => openImage(img.url)}
            aria-label={`Open ${img.description || "research image"}`}
          >
            <img
              src={img.url}
              alt={img.description || "Research image"}
              loading="lazy"
              className="image-card-preview"
              onError={(e) => {
                e.currentTarget.closest(".image-card").style.display = "none";
              }}
            />

            {img.description && (
              <div className="image-card-description">
                {img.description}
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}