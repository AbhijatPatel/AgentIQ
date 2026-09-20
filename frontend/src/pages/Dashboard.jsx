import { lazy, Suspense, useState, useEffect, useRef } from "react";
import { useResearch } from "../hooks/useResearch";
import { uploadDocument } from "../services/api";
import AgentStatus from "../components/AgentStatus";
import ResearchSteps from "../components/ResearchSteps";

const ReportViewer = lazy(() => import("../components/ReportViewer"));
const SourceViewer = lazy(() => import("../components/SourceViewer"));
const ImageGallery = lazy(() => import("../components/ImageGallery"));
const VideoGallery = lazy(() => import("../components/VideoGallery"));

const MIN_GOAL_LENGTH = 5;

export default function Dashboard({ researchHook: passedHook, onNavigateToHistory }) {
  const [goalInput, setGoalInput] = useState("");
  const [activeFilter, setActiveFilter] = useState(null);
  const [activeResultTab, setActiveResultTab] = useState("all");
  const [attachments, setAttachments] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [isUploadingFiles, setIsUploadingFiles] = useState(false);
  const [showAttachMenu, setShowAttachMenu] = useState(false);

  const imageInputRef = useRef(null);
  const docInputRef = useRef(null);
  const attachMenuRef = useRef(null);
  const recognitionRef = useRef(null);

  // Close attach dropdown menu on outside click or Escape key
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        attachMenuRef.current &&
        !attachMenuRef.current.contains(e.target)
      ) {
        setShowAttachMenu(false);
      }
    };
    const handleEsc = (e) => {
      if (e.key === "Escape") {
        setShowAttachMenu(false);
      }
    };
    if (showAttachMenu) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleEsc);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEsc);
    };
  }, [showAttachMenu]);

  const internalHook = useResearch();
  const {
    status,
    events,
    result,
    error,
    run,
    reset,
  } = passedHook || internalHook;

  const isRunning = status === "running" || isUploadingFiles;
  const canSubmit =
    (goalInput.trim().length >= MIN_GOAL_LENGTH || attachments.length > 0) &&
    !isRunning;

  // If a past session is loaded that has a user_goal, update the prompt field if empty
  useEffect(() => {
    if (result?.user_goal && !goalInput) {
      setGoalInput(result.user_goal);
    }
  }, [result?.user_goal]);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!canSubmit) return;

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }

    setActiveResultTab("all");

    let promptText = goalInput.trim();
    if (!promptText && attachments.length > 0) {
      promptText = "Analyze and summarize the key findings from the attached materials.";
    }

    // If attachments exist, index them into RAG
    if (attachments.length > 0) {
      setIsUploadingFiles(true);
      try {
        const indexedNames = [];
        for (const item of attachments) {
          try {
            const res = await uploadDocument(item.file);
            indexedNames.push(res.filename || item.name);
          } catch (uploadErr) {
            console.warn(`Failed to upload ${item.name}:`, uploadErr);
          }
        }
        if (indexedNames.length > 0) {
          promptText += ` [Referenced Files: ${indexedNames.join(", ")}]`;
        }
      } finally {
        setIsUploadingFiles(false);
      }
    }

    run(promptText);
  };

  const handleKeyDown = (e) => {
    // Enter (without Shift) or Ctrl/Cmd + Enter submits
    if (
      (e.key === "Enter" && !e.shiftKey) ||
      ((e.ctrlKey || e.metaKey) && e.key === "Enter")
    ) {
      e.preventDefault();
      if (canSubmit) {
        handleSubmit(e);
      }
    } else if (e.key === "Escape" && goalInput.length > 0 && !isRunning) {
      e.preventDefault();
      setGoalInput("");
    }
  };

  const handleReset = () => {
    reset();
    setGoalInput("");
    setAttachments((prev) => {
      prev.forEach((item) => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
      return [];
    });
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
    setActiveResultTab("all");
  };

  const toggleListening = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert(
        "Voice speech recognition is not supported in this browser. Please use Google Chrome, Microsoft Edge, or Safari."
      );
      return;
    }

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = navigator.language || "en-US";

      let initialText = goalInput;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript) {
          setGoalInput(
            initialText ? `${initialText} ${transcript}` : transcript
          );
        }
      };

      recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error("Voice recognition start error:", err);
      setIsListening(false);
    }
  };

  const handleAddFiles = (fileList) => {
    const newItems = Array.from(fileList).map((file) => {
      const isImg = file.type.startsWith("image/");
      return {
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        file,
        name: file.name,
        size: (file.size / 1024).toFixed(1) + " KB",
        type: file.type,
        isImage: isImg,
        previewUrl: isImg ? URL.createObjectURL(file) : null,
      };
    });
    setAttachments((prev) => [...prev, ...newItems]);
  };

  const handleRemoveAttachment = (id) => {
    setAttachments((prev) => {
      const item = prev.find((a) => a.id === id);
      if (item?.previewUrl) URL.revokeObjectURL(item.previewUrl);
      return prev.filter((a) => a.id !== id);
    });
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleAddFiles(e.target.files);
      e.target.value = "";
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDraggingOver) setIsDraggingOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleAddFiles(e.dataTransfer.files);
    }
  };

  const hasResults = Boolean(
    result?.final_report ||
      (result?.evidence && result.evidence.length > 0) ||
      (result?.images && result.images.length > 0) ||
      (result?.videos && result.videos.length > 0)
  );

  return (
    <div className="dashboard-page">
      <header className="app-header">
        <div className="eyebrow">
          <span className="eyebrow-dot" aria-hidden="true" />
          Autonomous Multi-Agent Intelligence
        </div>
        <h1>
          Autonomous Intelligence{" "}
          <span className="gradient-text">Workspace</span>
        </h1>
        <p>
          Research anything. Understand everything.
        </p>
      </header>

      <div className="research-workspace">
        <section className="research-main" aria-label="Research workspace">
          {/* Main Studio Composer Card */}
          <form
            onSubmit={handleSubmit}
            className={`goal-form ${isDraggingOver ? "goal-form--drag-over" : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {/* Hidden File Inputs for Image & Document */}
            <input
              type="file"
              ref={imageInputRef}
              onChange={handleFileChange}
              multiple
              accept="image/*,.png,.jpg,.jpeg,.webp"
              style={{ display: "none" }}
            />
            <input
              type="file"
              ref={docInputRef}
              onChange={handleFileChange}
              multiple
              accept=".pdf,.txt,.md,.csv,.doc,.docx"
              style={{ display: "none" }}
            />

            <div className="composer-header">
              <label htmlFor="research-goal" className="composer-label">
                <span className="composer-label-icon">✦</span> Deep Research Query
              </label>
              <span className="composer-tagline">
                Explore topics with autonomous multi-agent intelligence
              </span>
            </div>

            {/* Attached Files / Images Preview Row */}
            {attachments.length > 0 && (
              <div
                className="composer-attachments-row"
                aria-label="Attached files and images"
              >
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    className="attachment-chip"
                    title={`${att.name} (${att.size})`}
                  >
                    {att.isImage ? (
                      <div className="attachment-thumb-wrap">
                        <img
                          src={att.previewUrl}
                          alt={att.name}
                          className="attachment-thumb-img"
                        />
                      </div>
                    ) : (
                      <span className="attachment-doc-icon" aria-hidden="true">
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                          <polyline points="14 2 14 8 20 8" />
                        </svg>
                      </span>
                    )}
                    <span className="attachment-name">{att.name}</span>
                    <span className="attachment-size">{att.size}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveAttachment(att.id)}
                      className="attachment-remove-btn"
                      title={`Remove ${att.name}`}
                      aria-label={`Remove ${att.name}`}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="composer-input-shell">
              <textarea
                id="research-goal"
                className="goal-textarea"
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="What would you like AgentIQ to investigate? (e.g. compare architectures, explore breakthroughs, uncover evidence...)"
                disabled={isRunning}
                rows={4}
                minLength={attachments.length > 0 ? 0 : MIN_GOAL_LENGTH}
                maxLength={5000}
                aria-label="Research goal"
                aria-describedby="goal-help"
              />
            </div>

            <div className="composer-footer">
              <div className="composer-footer-left">
                {/* File Attachment Button with Dropdown Menu */}
                <div className="attach-menu-anchor" ref={attachMenuRef}>
                  <button
                    type="button"
                    onClick={() => setShowAttachMenu((prev) => !prev)}
                    className={`composer-tool-btn ${showAttachMenu ? "composer-tool-btn--active" : ""}`}
                    title="Attach an image or file"
                    aria-expanded={showAttachMenu}
                    aria-haspopup="menu"
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      aria-hidden="true"
                    >
                      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l7.88-7.88" />
                    </svg>
                    <span>Attach</span>
                    {attachments.length > 0 && (
                      <span className="tool-badge-count">{attachments.length}</span>
                    )}
                  </button>

                  {/* Dropdown Options: Image or File */}
                  {showAttachMenu && (
                    <div className="attach-menu-popover" role="menu">
                      <button
                        type="button"
                        role="menuitem"
                        className="attach-menu-item"
                        onClick={() => {
                          setShowAttachMenu(false);
                          imageInputRef.current?.click();
                        }}
                      >
                        <span className="attach-item-icon" aria-hidden="true">
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                            <circle cx="9" cy="9" r="2" />
                            <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
                          </svg>
                        </span>
                        <div className="attach-item-info">
                          <span className="attach-item-title">Upload Image</span>
                          <span className="attach-item-desc">PNG, JPG, WebP</span>
                        </div>
                      </button>

                      <button
                        type="button"
                        role="menuitem"
                        className="attach-menu-item"
                        onClick={() => {
                          setShowAttachMenu(false);
                          docInputRef.current?.click();
                        }}
                      >
                        <span className="attach-item-icon" aria-hidden="true">
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                            <line x1="16" x2="8" y1="13" y2="13" />
                            <line x1="16" x2="8" y1="17" y2="17" />
                          </svg>
                        </span>
                        <div className="attach-item-info">
                          <span className="attach-item-title">Upload File</span>
                          <span className="attach-item-desc">PDF, TXT, MD, CSV</span>
                        </div>
                      </button>
                    </div>
                  )}
                </div>

                {/* Voice Speech-to-Text Button */}
                <button
                  type="button"
                  onClick={toggleListening}
                  className={`composer-tool-btn voice-btn ${isListening ? "voice-btn--listening" : ""}`}
                  title={isListening ? "Stop listening" : "Speak your research prompt"}
                  aria-label={isListening ? "Stop voice dictation" : "Start voice dictation"}
                >
                  {isListening ? (
                    <>
                      <span className="voice-pulse-dot" aria-hidden="true" />
                      <span>Listening...</span>
                    </>
                  ) : (
                    <>
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                        <line x1="12" y1="19" x2="12" y2="22" />
                      </svg>
                      <span>Voice</span>
                    </>
                  )}
                </button>

                <span className="footer-separator" aria-hidden="true">·</span>

                <span className="char-count-pill">
                  {goalInput.length}/5,000 characters
                </span>

                {goalInput.length > 0 && !isRunning && (
                  <button
                    type="button"
                    onClick={() => setGoalInput("")}
                    className="composer-clear-link"
                    title="Clear prompt (Esc)"
                  >
                    Clear
                  </button>
                )}

                {goalInput.trim().length > 0 &&
                  goalInput.trim().length < MIN_GOAL_LENGTH &&
                  attachments.length === 0 && (
                    <span className="char-count-alert">
                      Min {MIN_GOAL_LENGTH} characters
                    </span>
                  )}
              </div>

              <div className="button-row">
                {(status !== "idle" || hasResults) && (
                  <button
                    type="button"
                    onClick={handleReset}
                    className="secondary-btn"
                    title="Clear current session and start new research query"
                  >
                    <span className="btn-icon-wrap" aria-hidden="true">
                      <svg
                        className="reset-icon"
                        width="13"
                        height="13"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
                        <path d="M21 3v5h-5" />
                        <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
                        <path d="M8 16H3v5" />
                      </svg>
                    </span>
                    <span>New research</span>
                  </button>
                )}

                <button
                  type="submit"
                  disabled={!canSubmit}
                  className={`start-research-btn ${canSubmit ? "start-research-btn--active" : ""}`}
                  aria-busy={isRunning}
                  title="Run research (Enter)"
                >
                  {isRunning ? (
                    <>
                      <span className="loading-spinner" aria-hidden="true" />
                      <span>{isUploadingFiles ? "Uploading files..." : "Investigating..."}</span>
                    </>
                  ) : (
                    <>
                      <span className="btn-sparkle-dot" aria-hidden="true">✦</span>
                      <span>Start research</span>
                      <span className="btn-arrow" aria-hidden="true">→</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>

          {/* Pipeline Card */}
          {status !== "idle" && (
            <section className="pipeline-card" aria-live="polite">
              <div className="pipeline-header">
                <div>
                  <div className="section-kicker">Live workflow</div>
                  <h2>Research pipeline</h2>
                  <p>
                    {status === "running"
                      ? "Your research team is actively investigating across sources."
                      : status === "completed"
                      ? "Research pipeline completed successfully."
                      : "Research ended with an error."}
                  </p>
                </div>
                <span className={`status-badge status-${status}`}>{status}</span>
              </div>
              <AgentStatus
                events={events}
                activeFilter={activeFilter}
                onFilterChange={setActiveFilter}
              />
              <ResearchSteps events={events} activeFilter={activeFilter} />
            </section>
          )}

          {error && <div className="error-alert" role="alert">{error}</div>}

          {result?.errors?.length > 0 && (
            <div className="warning-alert" role="status">
              <strong>Some steps need attention</strong>
              <span>The pipeline continued, but a few agent outputs were incomplete.</span>
              <ul>
                {result.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Result Section Navigation Tabs */}
          {hasResults && (
            <div className="results-nav-wrapper">
              <div className="results-nav-bar" role="tablist" aria-label="Research output sections">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeResultTab === "all"}
                  className={`results-nav-btn ${
                    activeResultTab === "all" ? "results-nav-btn--active" : ""
                  }`}
                  onClick={() => setActiveResultTab("all")}
                >
                  <span className="results-nav-icon">📑</span> All Sections
                </button>

                {result?.final_report && (
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeResultTab === "report"}
                    className={`results-nav-btn ${
                      activeResultTab === "report" ? "results-nav-btn--active" : ""
                    }`}
                    onClick={() => setActiveResultTab("report")}
                  >
                    <span className="results-nav-icon">📄</span> Report
                  </button>
                )}

                {result?.evidence && result.evidence.length > 0 && (
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeResultTab === "sources"}
                    className={`results-nav-btn ${
                      activeResultTab === "sources" ? "results-nav-btn--active" : ""
                    }`}
                    onClick={() => setActiveResultTab("sources")}
                  >
                    <span className="results-nav-icon">📚</span> Sources
                    <span className="results-nav-count">{result.evidence.length}</span>
                  </button>
                )}

                {result?.images && result.images.length > 0 && (
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeResultTab === "images"}
                    className={`results-nav-btn ${
                      activeResultTab === "images" ? "results-nav-btn--active" : ""
                    }`}
                    onClick={() => setActiveResultTab("images")}
                  >
                    <span className="results-nav-icon">🖼️</span> Images
                    <span className="results-nav-count">{result.images.length}</span>
                  </button>
                )}

                {result?.videos && result.videos.length > 0 && (
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeResultTab === "videos"}
                    className={`results-nav-btn ${
                      activeResultTab === "videos" ? "results-nav-btn--active" : ""
                    }`}
                    onClick={() => setActiveResultTab("videos")}
                  >
                    <span className="results-nav-icon">🎬</span> Videos
                    <span className="results-nav-count">{result.videos.length}</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Research Results Sections */}
          <div className="results-container">
            {result?.final_report &&
              (activeResultTab === "all" || activeResultTab === "report") && (
                <Suspense
                  fallback={
                    <div className="result-section-card report-section-card loading-skeleton">
                      Loading report...
                    </div>
                  }
                >
                  <section className="result-section-card report-section-card" id="section-report">
                    <ReportViewer
                      report={result.final_report}
                      critique={result.critique}
                    />
                  </section>
                </Suspense>
              )}

            {result?.evidence &&
              result.evidence.length > 0 &&
              (activeResultTab === "all" || activeResultTab === "sources") && (
                <Suspense
                  fallback={
                    <div className="result-section-card sources-section-card loading-skeleton">
                      Loading sources...
                    </div>
                  }
                >
                  <section className="result-section-card sources-section-card" id="section-sources">
                    <SourceViewer evidence={result.evidence} />
                  </section>
                </Suspense>
              )}

            {result?.images &&
              result.images.length > 0 &&
              (activeResultTab === "all" || activeResultTab === "images") && (
                <Suspense
                  fallback={
                    <div className="result-section-card images-section-card loading-skeleton">
                      Loading visual assets...
                    </div>
                  }
                >
                  <section className="result-section-card images-section-card" id="section-images">
                    <ImageGallery images={result.images} />
                  </section>
                </Suspense>
              )}

            {result?.videos &&
              result.videos.length > 0 &&
              (activeResultTab === "all" || activeResultTab === "videos") && (
                <Suspense
                  fallback={
                    <div className="result-section-card videos-section-card loading-skeleton">
                      Loading multimedia...
                    </div>
                  }
                >
                  <section className="result-section-card videos-section-card" id="section-videos">
                    <VideoGallery videos={result.videos} />
                  </section>
                </Suspense>
              )}
          </div>
        </section>
      </div>
    </div>
  );
}