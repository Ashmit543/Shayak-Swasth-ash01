"""
Multi-Agent System for Healthcare Management

This module implements a multi-agent architecture for handling:
- Data Ingestion (file uploads to Supabase Storage and metadata storage)
- Medical Insights (text extraction, embeddings, summaries)
- Query & Compliance (RAG-based queries with role-based access)
"""

from .base_agent import BaseAgent
from .data_ingestion_agent import DataIngestionAgent
from .medical_insights_agent import MedicalInsightsAgent
from .query_compliance_agent import QueryComplianceAgent
from .agent_manager import AgentManager
from .langchain_medical_insights import LangChainMedicalInsightsAgent
from .langchain_query_agent import LangChainQueryAgent

__all__ = [
    "BaseAgent",
    "DataIngestionAgent",
    "MedicalInsightsAgent",
    "QueryComplianceAgent",
    "LangChainMedicalInsightsAgent",
    "LangChainQueryAgent",
    "AgentManager",
]

