import sys
sys.path.insert(0, r'C:\Users\pilli\Downloads\rag system\phase2')
from config import DEFAULT_CONFIG
from embeddings import EmbeddingGenerator
from chunking import StructureAwareChunker
from loader import Phase1Loader
from qdrant_store import QdrantStore
from preprocessing import clean_pages

# Check chunking
loader = Phase1Loader()
docs = loader.load_all_documents()
print('Documents loaded:', len(docs))

chunker = StructureAwareChunker(DEFAULT_CONFIG)
all_chunks = []
for doc in docs:
    pages = doc.get('pages', [])
    chunks = chunker.chunk_document(doc['document_id'], pages)
    all_chunks.extend(chunks)
print('Total chunks:', len(all_chunks))

# Check Qdrant
store = QdrantStore(DEFAULT_CONFIG)
info = store.get_collection_info()
print('Qdrant vectors:', info.get('vectors_count', 'N/A'))
print('Qdrant points:', info.get('points_count', 'N/A'))