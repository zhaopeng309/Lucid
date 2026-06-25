import os
import pytest
from unittest.mock import patch, MagicMock
from src.regulation_ingester import RegulationIngester

@patch('src.regulation_ingester.chromadb.PersistentClient')
@patch('src.regulation_ingester.genai.embed_content')
def test_regulation_ingester_flow(mock_embed, mock_chroma):
    mock_collection = MagicMock()
    mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
    
    # Mock embedding return
    mock_embed.return_value = {"embedding": [0.2] * 768}
    
    ingester = RegulationIngester(db_path=":memory:")
    
    # Check chunking logic (500 chars limit, 50 overlap)
    text = "A" * 1200
    chunks = ingester.chunk_text(text, max_chunk_size=500, overlap=50)
    # 0-500, 450-950, 900-1200 -> 3 chunks
    assert len(chunks) == 3
    assert chunks[0] == "A" * 500
    assert chunks[1] == "A" * 500
    assert chunks[2] == "A" * 300
    
    # Test ingestion
    with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
        ingester.ingest_regulation("Peking University", 2026, "General", "Hello regulation text!")
        
        # Verify get_embedding was called
        assert mock_embed.called
        # Verify text-embedding-004 model was specified
        mock_embed.assert_called_with(
            model="models/text-embedding-004",
            content="Hello regulation text!",
            task_type="retrieval_document"
        )
        # Verify collection.add was called
        assert mock_collection.add.called
