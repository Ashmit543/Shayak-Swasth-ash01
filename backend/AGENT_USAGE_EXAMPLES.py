"""
Example Usage: Using Updated Agents with LangChain + FAISS

This shows how to use the updated 5 agents with FAISS integration.
It's simpler than you'd expect! 🎯
"""

from sqlalchemy.orm import Session
from agents.data_ingestion_agent import DataIngestionAgent
from agents.medical_insights_agent import MedicalInsightsAgent
from agents.query_compliance_agent import QueryComplianceAgent
from agents.faiss_utils import vectorstore_exists, list_vectorstores
import uuid

# Initialize agents
data_agent = DataIngestionAgent()
insights_agent = MedicalInsightsAgent()
query_agent = QueryComplianceAgent()

# Example IDs
patient_id = uuid.uuid4()
user_id = uuid.uuid4()
record_id = uuid.uuid4()


# ============================================================================
# EXAMPLE 1: Upload & Process Medical Record
# ============================================================================
async def example_upload_and_process():
    """Upload a file and process it with FAISS"""
    
    db: Session  # Your database session
    
    # 1. Upload file
    # This calls DataIngestionAgent which now uses LangChain loaders
    record = await data_agent.ingest_record(
        db=db,
        file=uploaded_file,  # FastAPI UploadFile
        patient_id=patient_id,
        user_id=user_id,
        title="Patient Lab Report"
    )
    
    print(f"✅ Record created: {record.id}")
    
    # 2. Process with MedicalInsightsAgent (usually async via Celery)
    # This creates FAISS vectorstore automatically
    result = await insights_agent.process_record(
        db=db,
        record_id=record.id
    )
    
    print(f"✅ FAISS vectorstore created")
    print(f"   - Text extracted: {result['text_chunks']} chunks")
    print(f"   - Embeddings created: {len(result['embeddings'])} embeddings")
    
    # Verify FAISS was saved
    if vectorstore_exists(record.id):
        print(f"✅ FAISS vectorstore saved to disk")


# ============================================================================
# EXAMPLE 2: Query Records with LangChain RAG + FAISS
# ============================================================================
def example_semantic_search():
    """Semantic search using FAISS (10-100x faster!)"""
    
    db: Session
    
    # Fast semantic search using FAISS
    results = query_agent.semantic_search(
        db=db,
        user_id=user_id,
        query="What are the patient's glucose levels?",
        top_k=3
    )
    
    print(f"✅ Semantic search results:")
    for i, result in enumerate(results['results'], 1):
        print(f"   {i}. Score: {result['similarity']:.3f}")
        print(f"      Text: {result['content'][:100]}...")


# ============================================================================
# EXAMPLE 3: Question Answering with LangChain RAG
# ============================================================================
def example_rag_question_answering():
    """Ask questions with LangChain RAG + FAISS"""
    
    db: Session
    
    # LangChain RetrievalQA chain automatically:
    # 1. Loads FAISS vectorstore
    # 2. Retrieves relevant documents
    # 3. Generates answer with context
    result = query_agent.ask_question(
        db=db,
        user_id=user_id,
        patient_id=patient_id,
        record_id=record_id,
        question="What medications should be prescribed?"
    )
    
    print(f"✅ Q&A Answer:")
    print(f"   Question: {result['question']}")
    print(f"   Answer: {result['answer']}")
    print(f"   Source: {result.get('source_documents', [])[0] if result.get('source_documents') else 'None'}")


# ============================================================================
# EXAMPLE 4: Using FAISS Utilities
# ============================================================================
def example_faiss_utilities():
    """Use simple FAISS utilities"""
    
    from agents.faiss_utils import (
        init_vectorstore_dir,
        get_vectorstore_path,
        vectorstore_exists,
        list_vectorstores
    )
    
    # Initialize vectorstore directory
    vectorstore_dir = init_vectorstore_dir()
    print(f"✅ Vectorstore directory: {vectorstore_dir}")
    
    # Check if vectorstore exists for a record
    record_id = uuid.uuid4()
    if vectorstore_exists(record_id):
        path = get_vectorstore_path(record_id)
        print(f"✅ Vectorstore found: {path}")
    else:
        print(f"❌ Vectorstore not found for record: {record_id}")
    
    # List all vectorstores
    all_records = list_vectorstores()
    print(f"✅ Total vectorstores: {len(all_records)}")
    for rec_id in all_records[:5]:  # Show first 5
        print(f"   - record_{rec_id}")


# ============================================================================
# EXAMPLE 5: PoC Agents (Optional - for migration path)
# ============================================================================
def example_poc_agents():
    """Use enhanced PoC agents"""
    
    from agents.langchain_medical_insights import LangChainMedicalInsightsAgent
    from agents.langchain_query_agent import LangChainQueryAgent
    
    poc_insights = LangChainMedicalInsightsAgent()
    poc_query = LangChainQueryAgent()
    
    db: Session
    
    # Process record with PoC agent
    result = poc_insights.process_record(
        db=db,
        record_id=record_id
    )
    print(f"✅ PoC insights agent created FAISS vectorstore")
    
    # Query with PoC agent
    answer = poc_query.ask_question(
        db=db,
        user_id=user_id,
        patient_id=patient_id,
        record_id=record_id,
        question="What's the diagnosis?"
    )
    print(f"✅ PoC query agent answer: {answer}")


# ============================================================================
# EXAMPLE 6: Full Workflow
# ============================================================================
async def example_full_workflow():
    """Complete workflow from upload to Q&A"""
    
    db: Session
    
    print("="*60)
    print("COMPLETE WORKFLOW: Upload → Process → Query")
    print("="*60)
    
    # Step 1: Upload file
    print("\n1️⃣  Uploading medical record...")
    record = await data_agent.ingest_record(
        db=db,
        file=uploaded_file,
        patient_id=patient_id,
        user_id=user_id,
        title="Lab Results"
    )
    print(f"   ✅ Record {record.id} created")
    
    # Step 2: Process with insights agent
    print("\n2️⃣  Processing with MedicalInsightsAgent...")
    insights_result = await insights_agent.process_record(db=db, record_id=record.id)
    print(f"   ✅ FAISS vectorstore created")
    print(f"   ✅ {len(insights_result['embeddings'])} embeddings saved")
    
    # Step 3: Query
    print("\n3️⃣  Querying with QueryComplianceAgent...")
    
    # 3a: Semantic search
    search_results = query_agent.semantic_search(
        db=db,
        user_id=user_id,
        query="glucose results",
        top_k=3
    )
    print(f"   ✅ Found {len(search_results['results'])} relevant documents")
    
    # 3b: RAG Question answering
    qa_result = query_agent.ask_question(
        db=db,
        user_id=user_id,
        patient_id=patient_id,
        record_id=record.id,
        question="What are the lab values?"
    )
    print(f"   ✅ Q&A Answer: {qa_result['answer'][:50]}...")
    
    print("\n" + "="*60)
    print("✅ WORKFLOW COMPLETE!")
    print("="*60)


# ============================================================================
# Key Benefits Shown in Examples:
# ============================================================================
"""
1️⃣  FAST SEARCH: FAISS is 10-100x faster than manual lookup
2️⃣  BETTER Q&A: LangChain RAG reduces hallucinations
3️⃣  SIMPLE CODE: No over-complication, just use the agents
4️⃣  BACKWARD COMPATIBLE: Old code still works
5️⃣  PoC AVAILABLE: LangChain PoC agents for reference

That's it! 🎉
"""
