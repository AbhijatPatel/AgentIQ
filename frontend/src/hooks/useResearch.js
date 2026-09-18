import { useCallback, useEffect, useRef, useState } from "react";
import { getResearchStatus, getResearchStreamUrl, startResearch } from "../services/api";

/**
 * useResearch centralizes all state and logic for running a research
 * session: starting it, listening to live events via SSE, and fetching
 * the final result when it completes.
 */
export function useResearch() {
  const [researchId, setResearchId] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | running | completed | failed
  const [events, setEvents] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const eventSourceRef = useRef(null);
  useEffect(() => {
  return () => {
    eventSourceRef.current?.close();
  };
}, []);

  const reset = useCallback(() => {
    eventSourceRef.current?.close();
    setResearchId(null);
    setStatus("idle");
    setEvents([]);
    setResult(null);
    setError(null);
  }, []);

  const run = useCallback(async (goal) => {
    reset();
    setStatus("running");

    try {
      const { research_id } = await startResearch(goal);
      setResearchId(research_id);

      const source = new EventSource(getResearchStreamUrl(research_id));
      eventSourceRef.current = source;

      source.onmessage = async (message) => {
        const payload = JSON.parse(message.data);

        if (payload.event === "done") {
          source.close();
          try {
            const finalStatus = await getResearchStatus(research_id);
            setResult(finalStatus);
            setStatus(finalStatus.status); // "completed" or "failed"
          } catch (err) {
            setError(err.message);
            setStatus("failed");
          }
          return;
        }

        if (payload.event === "error") {
          setError(payload.message || "Stream error");
          source.close();
          setStatus("failed");
          return;
        }

        setEvents((prev) => [...prev, payload]);
      };

      source.onerror = () => {
        // EventSource retries automatically on transient errors; only
        // treat it as fatal if the connection is fully closed.
        if (source.readyState === EventSource.CLOSED) {
          setError("Connection to server lost.");
          setStatus("failed");
        }
      };
    } catch (err) {
      setError(err.message);
      setStatus("failed");
    }
  }, [reset]);

  const loadPastSession = useCallback((sessionData) => {
    eventSourceRef.current?.close();
    setResearchId(sessionData.research_id);
    setEvents(sessionData.agent_events || []);
    setResult(sessionData);
    setStatus(sessionData.status);
    setError(null);
  }, []);

  return { researchId, status, events, result, error, run, reset, loadPastSession };
}