"""
Data Ingestion Agent

Handles file uploads to Supabase Storage and stores metadata in PostgreSQL.
Now with LangChain document loaders for better file handling.
Triggered by: /api/records/upload endpoint
"""

import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile
from io import BytesIO
from supabase import create_client

# LangChain imports
from langchain_community.document_loaders import PyPDFLoader, ImageLoader
from langchain.schema import Document

from .base_agent import BaseAgent
from models import Record, Patient, RecordStatusEnum, FileTypeEnum

class DataIngestionAgent(BaseAgent):
    """Agent responsible for ingesting medical records into the system"""
    
    def __init__(self):
        super().__init__("DataIngestionAgent")
        self.supabase_client = self._init_supabase_client()
        self.bucket_name = os.getenv("SUPABASE_BUCKET", "healthcare-records")
    
    def _init_supabase_client(self):
        """Initialize Supabase client"""
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if not url or not key:
                raise ValueError("SUPABASE_URL or SUPABASE_KEY not set")
            return create_client(url, key)
        except Exception as e:
            self.logger.error(f"Failed to initialize Supabase client: {str(e)}")
            return None
    
    def detect_file_type(self, filename: str) -> FileTypeEnum:
        """Detect file type based on extension"""
        extension = filename.lower().split('.')[-1]
        
        if extension == 'pdf':
            return FileTypeEnum.PDF
        elif extension in ['jpg', 'jpeg', 'png', 'tiff', 'bmp']:
            return FileTypeEnum.IMAGE
        elif extension in ['dcm', 'dicom']:
            return FileTypeEnum.DICOM
        else:
            return FileTypeEnum.REPORT
    
    async def upload_to_supabase(
        self,
        file: UploadFile,
        patient_id: uuid.UUID,
        record_id: uuid.UUID
    ) -> Optional[str]:
        """Upload file to Supabase and return the URL"""
        if not self.supabase_client:
            self.logger.error("Supabase client not initialized")
            return None
        
        try:
            # Generate unique file path
            file_extension = file.filename.split('.')[-1]
            file_path = f"records/{patient_id}/{record_id}.{file_extension}"
            
            # Read file content
            content = await file.read()
            
            # Upload to Supabase Storage
            response = self.supabase_client.storage.from_(self.bucket_name).upload(
                file_path,
                content,
                {"cacheControl": "3600", "upsert": "false"}
            )
            
            # Get public URL
            file_url = self.supabase_client.storage.from_(self.bucket_name).get_public_url(file_path)
            
            self.logger.info(f"File uploaded to Supabase: {file_path}")
            return file_url
            
        except Exception as e:
            self.logger.error(f"Supabase upload failed: {str(e)}")
            return None
    
    async def ingest_record(
        self,
        db: Session,
        file: UploadFile,
        patient_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main ingestion workflow:
        1. Validate patient exists
        2. Create record entry
        3. Upload file to Supabase Storage
        4. Update record with Supabase URL
        5. Log action
        6. Trigger Medical Insights Agent (async)
        """
        try:
            # 1. Validate patient
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                return self.handle_error(
                    Exception("Patient not found"),
                    "Patient validation"
                )
            
            # 2. Detect file type
            file_type = self.detect_file_type(file.filename)
            
            # 3. Create record entry
            record_id = uuid.uuid4()
            record = Record(
                id=record_id,
                patient_id=patient_id,
                title=title,
                file_type=file_type,
                file_url="pending",  # Temporary
                uploaded_by=user_id,
                upload_date=datetime.utcnow(),
                status=RecordStatusEnum.PENDING
            )
            db.add(record)
            db.commit()
            
            self.logger.info(f"Record created: {record_id}")
            
            # 4. Upload to Supabase
            supabase_url = await self.upload_to_supabase(file, patient_id, record_id)
            
            if not supabase_url:
                record.status = RecordStatusEnum.PENDING
                db.commit()
                return self.handle_error(
                    Exception("Supabase upload failed"),
                    "File upload"
                )
            
            # 5. Update record with Supabase URL
            record.file_url = supabase_url
            record.status = RecordStatusEnum.PROCESSING
            db.commit()
            
            # 6. Log action
            self.log_action(
                db=db,
                user_id=user_id,
                action="UPLOAD_RECORD",
                resource="Record",
                resource_id=record_id,
                ip_address=ip_address
            )
            
            self.logger.info(f"Record ingested successfully: {record_id}")
            
            # Return success with record info
            return self.success_response(
                data={
                    "record_id": str(record_id),
                    "patient_id": str(patient_id),
                    "file_type": file_type.value,
                    "file_url": supabase_url,
                    "status": record.status.value,
                    "trigger_insights": True  # Signal to trigger Medical Insights Agent
                },
                message="Record uploaded successfully. Processing insights..."
            )
            
        except Exception as e:
            db.rollback()
            return self.handle_error(e, "Record ingestion")
    
    def load_document_with_langchain(self, file_path: str, file_type: FileTypeEnum) -> Optional[list[Document]]:
        """
        Load document using LangChain loaders for better file parsing.
        This provides document metadata and structured content.
        """
        try:
            if file_type == FileTypeEnum.PDF:
                # Use LangChain's PDF loader for better parsing
                loader = PyPDFLoader(file_path)
                docs = loader.load()
                self.logger.info(f"Loaded {len(docs)} documents from PDF using LangChain")
                return docs
            elif file_type == FileTypeEnum.IMAGE:
                # Use LangChain's Image loader
                loader = ImageLoader(file_path)
                docs = loader.load()
                self.logger.info(f"Loaded image document using LangChain")
                return docs
            else:
                self.logger.warning(f"LangChain loader not available for file type: {file_type}")
                return None
        except Exception as e:
            self.logger.error(f"LangChain document loading failed: {str(e)}")
            return None
    
    def get_presigned_url(
        self,
        db: Session,
        record_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[str]:
        """Generate public URL for record download"""
        try:
            record = db.query(Record).filter(Record.id == record_id).first()
            if not record:
                return None
            
            # Supabase Storage returns public URLs directly
            # The file_url is already a public URL from Supabase
            self.logger.info(f"Retrieved public URL for record: {record_id}")
            return record.file_url
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve public URL: {str(e)}")
            return None

