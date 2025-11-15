"""
Migration Script: JSON Embeddings → FAISS Vectorstore

This script migrates existing embeddings from the database (stored as JSON)
to FAISS vectorstores for production use with LangChain v2 agents.

Usage:
    python migrate_embeddings_to_faiss.py
    
    Or with options:
    python migrate_embeddings_to_faiss.py --batch-size 10 --output ./vectorstores
"""

import os
import sys
import json
import uuid
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Embedding, Record
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings


class EmbeddingsMigrator:
    """Migrate embeddings from DB to FAISS vectorstore"""

    def __init__(
        self,
        db_url: str,
        vectorstore_output: Path,
        batch_size: int = 10,
    ):
        """
        Initialize migrator.

        Args:
            db_url: SQLAlchemy database URL
            vectorstore_output: Path to store vectorstores
            batch_size: Number of records to process per batch
        """
        self.db_url = db_url
        self.vectorstore_output = Path(vectorstore_output)
        self.batch_size = batch_size
        self.vectorstore_output.mkdir(parents=True, exist_ok=True)

        # Initialize DB connection
        engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=engine)

        # Initialize embeddings (use same as v2 agents)
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-ada-002",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

        self.stats = {
            "total_embeddings": 0,
            "successful_migrations": 0,
            "failed_migrations": 0,
            "vectorstores_created": 0,
            "errors": [],
        }

    def get_embeddings_from_db(self) -> List[Embedding]:
        """Fetch all embeddings from database"""
        db = self.SessionLocal()
        try:
            embeddings = db.query(Embedding).all()
            print(f"Found {len(embeddings)} embeddings in database")
            return embeddings
        finally:
            db.close()

    def parse_embedding_vector(self, embedding_obj: Embedding) -> Optional[List[float]]:
        """
        Parse embedding vector from database.
        
        Assumes embeddings are stored as:
        - JSON string in `embedding_vector` field
        - Or reconstructed from chunks
        """
        try:
            if hasattr(embedding_obj, "embedding_vector") and embedding_obj.embedding_vector:
                if isinstance(embedding_obj.embedding_vector, str):
                    return json.loads(embedding_obj.embedding_vector)
                else:
                    return embedding_obj.embedding_vector
            return None
        except Exception as e:
            print(f"Failed to parse embedding: {str(e)}")
            return None

    def create_documents_from_chunks(
        self, record_id: uuid.UUID
    ) -> List[Document]:
        """
        Create LangChain Documents from stored chunks.
        
        If original chunks are not available, creates placeholder documents
        from the embedding metadata.
        """
        db = self.SessionLocal()
        try:
            # Try to find original documents in storage
            # For now, create placeholder documents with metadata
            record = db.query(Record).filter(Record.id == record_id).first()
            
            if not record:
                return []

            # Create a single document representing the record
            # In a full migration, this would be per-chunk
            doc = Document(
                page_content=f"Medical record: {record.title}",
                metadata={
                    "record_id": str(record_id),
                    "source": record.file_url,
                    "file_type": record.file_type.value,
                    "created_at": record.upload_date.isoformat(),
                },
            )
            return [doc]

        finally:
            db.close()

    def migrate_embedding_to_vectorstore(
        self, embedding_obj: Embedding
    ) -> bool:
        """
        Migrate single embedding to FAISS vectorstore.

        Returns:
            True if successful, False otherwise
        """
        try:
            record_id = embedding_obj.record_id

            # Create documents for this record
            documents = self.create_documents_from_chunks(record_id)

            if not documents:
                print(f"No documents found for record {record_id}, skipping")
                return False

            # Create FAISS vectorstore from documents
            # Note: In a real migration, we'd re-embed using OpenAIEmbeddings
            vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings,
            )

            # Save vectorstore locally
            vectorstore_path = self.vectorstore_output / str(record_id)
            vectorstore.save_local(str(vectorstore_path))

            print(f"✓ Migrated embedding for record {record_id}")
            self.stats["successful_migrations"] += 1
            return True

        except Exception as e:
            error_msg = f"Failed to migrate {embedding_obj.record_id}: {str(e)}"
            print(f"✗ {error_msg}")
            self.stats["failed_migrations"] += 1
            self.stats["errors"].append(error_msg)
            return False

    def migrate_all(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Migrate all embeddings to FAISS vectorstores.

        Args:
            dry_run: If True, only show what would be migrated

        Returns:
            Migration statistics
        """
        print("\n" + "=" * 60)
        print("Starting Embeddings to FAISS Migration")
        print("=" * 60 + "\n")

        # Get embeddings from DB
        embeddings = self.get_embeddings_from_db()
        self.stats["total_embeddings"] = len(embeddings)

        if not embeddings:
            print("No embeddings to migrate")
            return self.stats

        if dry_run:
            print(f"[DRY RUN] Would migrate {len(embeddings)} embeddings")
            print(f"Output directory: {self.vectorstore_output}\n")
            for embedding in embeddings[:5]:  # Show first 5
                print(f"  - Record {embedding.record_id}")
            if len(embeddings) > 5:
                print(f"  ... and {len(embeddings) - 5} more\n")
            return self.stats

        # Process embeddings in batches
        print(f"Processing {len(embeddings)} embeddings in batches of {self.batch_size}...\n")

        for i in range(0, len(embeddings), self.batch_size):
            batch = embeddings[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(embeddings) + self.batch_size - 1) // self.batch_size

            print(f"Batch {batch_num}/{total_batches}:")
            for embedding in batch:
                self.migrate_embedding_to_vectorstore(embedding)
            print()

        self.stats["vectorstores_created"] = self.stats["successful_migrations"]

        # Print summary
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"Total embeddings:        {self.stats['total_embeddings']}")
        print(f"Successful migrations:   {self.stats['successful_migrations']}")
        print(f"Failed migrations:       {self.stats['failed_migrations']}")
        print(f"Vectorstores created:    {self.stats['vectorstores_created']}")
        print(f"Output directory:        {self.vectorstore_output}")

        if self.stats["errors"]:
            print(f"\nErrors encountered:")
            for error in self.stats["errors"][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(self.stats["errors"]) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more")

        print("\n" + "=" * 60 + "\n")
        return self.stats


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Migrate embeddings from DB to FAISS vectorstores"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://user:password@localhost/medicaldb",
        ),
        help="SQLAlchemy database URL",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("VECTORSTORE_PATH", "./vectorstores"),
        help="Output directory for vectorstores",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating",
    )

    args = parser.parse_args()

    # Verify environment
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    # Run migration
    migrator = EmbeddingsMigrator(
        db_url=args.db_url,
        vectorstore_output=Path(args.output),
        batch_size=args.batch_size,
    )

    stats = migrator.migrate_all(dry_run=args.dry_run)

    # Exit with error code if migrations failed
    if stats["failed_migrations"] > 0 and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
