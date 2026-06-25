import os
import chromadb
import google.generativeai as genai
from typing import List, Dict

class RegulationIngester:
    def __init__(self, db_path='data/chroma_db'):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.client.get_or_create_collection(name="college_regulations")
        
        # In a real environment, configure API key via environment variable
        api_key = os.environ.get("GEMINI_API_KEY", "mock_api_key")
        genai.configure(api_key=api_key)

    def chunk_text(self, text: str, max_chunk_size=500, overlap=50) -> List[str]:
        """
        Splits long text into smaller chunks with overlap.
        """
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start += max_chunk_size - overlap
        return chunks

    def get_embedding(self, text: str) -> List[float]:
        """
        Calls Gemini embedding model to convert text to vectors.
        """
        # If no real API key, return a mock embedding to avoid crashing
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key in [None, "", "mock_api_key"]:
             return [0.1] * 768
             
        try:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return [0.0] * 768

    def ingest_regulation(self, college_name: str, year: int, category: str, text: str):
        """
        Ingests a piece of admission regulation into ChromaDB.
        """
        chunks = self.chunk_text(text)
        
        ids = []
        embeddings = []
        metadatas = []
        documents = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{college_name}_{year}_{category}_{i}"
            embedding = self.get_embedding(chunk)
            
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk)
            metadatas.append({
                "college_name": college_name,
                "year": year,
                "category": category
            })
            
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        print(f"Successfully ingested {len(chunks)} chunks for {college_name} ({year}).")

if __name__ == "__main__":
    ingester = RegulationIngester()
    
    # Mock some data for testing
    sample_text = "根据学校规定，计算机科学与技术专业要求考生没有色盲和色弱。英语成绩需达到110分以上。"
    ingester.ingest_regulation(
        college_name="Peking University",
        year=2023,
        category="Eyesight",
        text=sample_text
    )
