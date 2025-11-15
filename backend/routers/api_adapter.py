"""
API Adapter Layer - Frontend Compatibility

This module ensures that API responses remain backward compatible
regardless of whether v1 or v2 agents are used internally.

Key responsibilities:
  1. Normalize response formats
  2. Handle v1/v2 response differences
  3. Provide migration utilities
  4. Log format changes for debugging
"""

from typing import Dict, Any, Optional
from datetime import datetime


def adapt_ingestion_response(
    agent_response: Dict[str, Any], agent_version: str = "v2"
) -> Dict[str, Any]:
    """
    Normalize data ingestion response to ensure frontend compatibility.

    Frontend expects:
    {
        "success": bool,
        "data": {
            "record_id": str,
            "patient_id": str,
            "file_type": str,
            "file_url": str,
            "status": str,
            "upload_date": str (ISO format)
        },
        "message": str
    }
    """
    if not agent_response.get("success"):
        return agent_response

    data = agent_response.get("data", {})

    # Ensure all required fields are present
    normalized = {
        "record_id": data.get("record_id"),
        "patient_id": data.get("patient_id"),
        "file_type": data.get("file_type", "REPORT"),
        "file_url": data.get("file_url") or data.get("s3_url"),
        "status": data.get("status", "PENDING"),
        "upload_date": datetime.utcnow().isoformat(),
        "trigger_insights": data.get("trigger_insights", True),
    }

    return {
        "success": True,
        "data": normalized,
        "message": agent_response.get("message", "Record uploaded successfully"),
    }


def adapt_search_response(
    agent_response: Dict[str, Any], agent_version: str = "v2"
) -> Dict[str, Any]:
    """
    Normalize semantic search response.

    Frontend expects:
    {
        "success": bool,
        "data": {
            "results": [
                {
                    "record_id": str,
                    "content": str,
                    "relevance_score": float,
                    "source": str,
                    "page": int
                },
                ...
            ],
            "count": int,
            "query_time_ms": int
        },
        "message": str
    }
    """
    if not agent_response.get("success"):
        return agent_response

    data = agent_response.get("data", {})
    results = data.get("results", [])

    # Normalize each result
    normalized_results = []
    for result in results:
        normalized_results.append(
            {
                "record_id": result.get("record_id"),
                "content": result.get("content", ""),
                "relevance_score": float(result.get("relevance_score", 0.0)),
                "source": result.get("source", "unknown"),
                "page": int(result.get("page", 0)),
            }
        )

    return {
        "success": True,
        "data": {
            "results": normalized_results,
            "count": len(normalized_results),
            "query_time_ms": data.get("query_time_ms", 0),
        },
        "message": agent_response.get("message", "Search completed"),
    }


def adapt_qa_response(
    agent_response: Dict[str, Any], agent_version: str = "v2"
) -> Dict[str, Any]:
    """
    Normalize Q&A response for frontend compatibility.

    Frontend expects:
    {
        "success": bool,
        "data": {
            "answer": str,
            "source_documents": [
                {
                    "content": str,
                    "source": str,
                    "page": int
                },
                ...
            ],
            "confidence": str ("high" | "medium" | "low"),
            "processing_time_ms": int
        },
        "message": str
    }
    """
    if not agent_response.get("success"):
        return agent_response

    data = agent_response.get("data", {})
    sources = data.get("source_documents", [])

    # Normalize source documents
    normalized_sources = []
    for source in sources:
        normalized_sources.append(
            {
                "content": source.get("content", "")[:500],  # Truncate for response
                "source": source.get("source", "unknown"),
                "page": int(source.get("page", 0)),
            }
        )

    return {
        "success": True,
        "data": {
            "answer": data.get("answer", "Unable to generate answer"),
            "source_documents": normalized_sources,
            "confidence": data.get("confidence", "medium"),
            "processing_time_ms": data.get("processing_time_ms", 0),
        },
        "message": agent_response.get("message", "Question answered"),
    }


def adapt_multi_turn_response(
    agent_response: Dict[str, Any], agent_version: str = "v2"
) -> Dict[str, Any]:
    """
    Normalize multi-turn conversation response.

    Frontend expects:
    {
        "success": bool,
        "data": {
            "answer": str,
            "source_documents": [...],
            "session_id": str,
            "turn_number": int,
            "can_continue": bool
        },
        "message": str
    }
    """
    if not agent_response.get("success"):
        return agent_response

    data = agent_response.get("data", {})
    sources = data.get("source_documents", [])

    normalized_sources = [
        {
            "content": source.get("content", "")[:500],
            "source": source.get("source", "unknown"),
            "page": int(source.get("page", 0)),
        }
        for source in sources
    ]

    return {
        "success": True,
        "data": {
            "answer": data.get("answer", "Unable to generate answer"),
            "source_documents": normalized_sources,
            "session_id": data.get("session_id"),
            "turn_number": data.get("turn_number", 1),
            "can_continue": True,  # Always allow continuation in v2
        },
        "message": agent_response.get("message", "Question answered"),
    }


class ResponseAdapter:
    """Utility class for adapting agent responses"""

    @staticmethod
    def ingestion(response: Dict[str, Any], version: str = "v2") -> Dict[str, Any]:
        """Adapt ingestion response"""
        return adapt_ingestion_response(response, version)

    @staticmethod
    def search(response: Dict[str, Any], version: str = "v2") -> Dict[str, Any]:
        """Adapt search response"""
        return adapt_search_response(response, version)

    @staticmethod
    def qa(response: Dict[str, Any], version: str = "v2") -> Dict[str, Any]:
        """Adapt Q&A response"""
        return adapt_qa_response(response, version)

    @staticmethod
    def multi_turn(response: Dict[str, Any], version: str = "v2") -> Dict[str, Any]:
        """Adapt multi-turn response"""
        return adapt_multi_turn_response(response, version)

    @staticmethod
    def normalize_all(
        response: Dict[str, Any],
        response_type: str,
        version: str = "v2",
    ) -> Dict[str, Any]:
        """
        Normalize any response type to frontend-compatible format.

        Args:
            response: Raw agent response
            response_type: Type of response ("ingestion", "search", "qa", "multi_turn")
            version: Agent version ("v1" or "v2")

        Returns:
            Normalized response compatible with frontend
        """
        adapters = {
            "ingestion": adapt_ingestion_response,
            "search": adapt_search_response,
            "qa": adapt_qa_response,
            "multi_turn": adapt_multi_turn_response,
        }

        adapter = adapters.get(response_type, lambda x, v: x)
        return adapter(response, version)
