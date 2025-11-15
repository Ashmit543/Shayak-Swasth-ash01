"""
FAISS Utilities for Vectorstore Management

Simple utilities for initializing and managing FAISS vectorstores
without overcomplicating the agent implementations.

Usage:
    from faiss_utils import init_vectorstore_dir, get_vectorstore_path
    
    # Initialize vectorstore directory
    vectorstore_dir = init_vectorstore_dir()
    
    # Get path for a record
    path = get_vectorstore_path(record_id)
"""

import os
from pathlib import Path
from typing import Optional
import uuid
import logging

logger = logging.getLogger("faiss_utils")


def init_vectorstore_dir(base_dir: str = "vectorstores") -> str:
    """
    Initialize the vectorstore directory.
    Creates it if it doesn't exist.
    
    Args:
        base_dir: Base directory name for vectorstores
    
    Returns:
        Path to vectorstore directory
    """
    vectorstore_path = Path(base_dir)
    vectorstore_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Initialized vectorstore directory: {vectorstore_path.resolve()}")
    return str(vectorstore_path.resolve())


def get_vectorstore_path(record_id: uuid.UUID, base_dir: str = "vectorstores") -> str:
    """
    Get the path for a record's FAISS vectorstore.
    
    Args:
        record_id: Record UUID
        base_dir: Base directory name for vectorstores
    
    Returns:
        Path to the vectorstore for this record
    """
    return os.path.join(base_dir, f"record_{record_id}")


def vectorstore_exists(record_id: uuid.UUID, base_dir: str = "vectorstores") -> bool:
    """
    Check if a vectorstore exists for a record.
    
    Args:
        record_id: Record UUID
        base_dir: Base directory name for vectorstores
    
    Returns:
        True if vectorstore exists, False otherwise
    """
    path = get_vectorstore_path(record_id, base_dir)
    return os.path.isdir(path) and os.path.exists(os.path.join(path, "index.faiss"))


def list_vectorstores(base_dir: str = "vectorstores") -> list[str]:
    """
    List all existing vectorstores.
    
    Args:
        base_dir: Base directory name for vectorstores
    
    Returns:
        List of record IDs with existing vectorstores
    """
    if not os.path.exists(base_dir):
        return []
    
    record_ids = []
    for item in os.listdir(base_dir):
        if item.startswith("record_"):
            record_ids.append(item.replace("record_", ""))
    return record_ids


def cleanup_old_vectorstores(base_dir: str = "vectorstores", days: int = 30) -> int:
    """
    Clean up vectorstores older than specified days.
    Useful for maintenance.
    
    Args:
        base_dir: Base directory name for vectorstores
        days: Delete vectorstores older than this many days
    
    Returns:
        Number of vectorstores deleted
    """
    import shutil
    import time
    
    if not os.path.exists(base_dir):
        return 0
    
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    deleted_count = 0
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            if os.path.getmtime(item_path) < cutoff_time:
                try:
                    shutil.rmtree(item_path)
                    deleted_count += 1
                    logger.info(f"Deleted old vectorstore: {item}")
                except Exception as e:
                    logger.error(f"Failed to delete vectorstore {item}: {e}")
    
    return deleted_count


# Environment configuration
VECTORSTORE_DIR = os.getenv("LANGCHAIN_VSTORE_DIR", "vectorstores")
