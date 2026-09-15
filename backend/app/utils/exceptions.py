"""
Centralized exception hierarchy for AgentIQ.

Every custom exception in the app (PlannerError, WriterError,
WebSearchError, DocumentLoadError, etc.) already exists in its own
module. This file defines a small set of BASE categories that let the
global error handler classify any exception into a consistent HTTP
response, without every module needing to import from a central place.

Rather than forcing every existing exception to inherit from a new
base class (which would mean touching a dozen files), the error
handler in error_handlers.py uses type-name matching. This file
documents the categories and provides a couple of NEW exception types
for truly generic/unclassified failures.
"""

from __future__ import annotations


class AgentIQError(Exception):
    """Base class for any AgentIQ-specific application error."""


class ConfigurationError(AgentIQError):
    """Raised when required configuration (API keys, DB URL, etc.) is missing or invalid."""


class ExternalServiceError(AgentIQError):
    """Raised when a third-party service (LLM, search, embeddings) fails unexpectedly."""


# Map of exception class names -> (http_status, error_code, user_facing_message)
# Used by error_handlers.py to classify exceptions raised anywhere in the app
# without requiring every module to share a common base class.
ERROR_CLASSIFICATION: dict[str, tuple[int, str, str]] = {
    # LLM errors
    "LLMClientError": (502, "llm_error", "The AI service failed to respond correctly. Please try again."),
    # Agent errors
    "PlannerError": (502, "planner_error", "Failed to plan research tasks."),
    "ResearcherError": (502, "researcher_error", "Failed to gather research evidence."),
    "WriterError": (502, "writer_error", "Failed to generate the report."),
    "CriticError": (502, "critic_error", "Failed to evaluate the report."),
    "RevisionLoopError": (502, "revision_error", "Failed to complete the report revision process."),
    # Tool errors
    "WebSearchError": (502, "web_search_error", "Web search failed. Please try again."),
    "DocumentLoadError": (400, "document_error", "The document could not be processed."),
    # Database errors
    "OperationalError": (503, "database_unavailable", "The database is temporarily unavailable."),
    "IntegrityError": (409, "database_conflict", "A data conflict occurred."),
}


def classify_exception(exc: Exception) -> tuple[int, str, str]:
    """
    Return (http_status, error_code, user_message) for a given exception,
    based on its class name. Falls back to a generic 500 for anything
    not explicitly classified.
    """
    exc_name = type(exc).__name__
    return ERROR_CLASSIFICATION.get(
        exc_name,
        (500, "internal_error", "An unexpected error occurred. Please try again."),
    )