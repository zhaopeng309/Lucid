import os
import pytest
from unittest.mock import patch, MagicMock

from src.scraper import AdmissionsScraper
from src.regulation_ingester import RegulationIngester
from src.audit import AutomatedAudit

class TestPhase2And3:
    
    @patch('src.scraper.sqlite3.connect')
    def test_admissions_scraper(self, mock_connect):
        """测试 AdmissionsScraper 数据解析和导入流程"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # 避免真正创建文件
        scraper = AdmissionsScraper(db_path=":memory:")
        
        # 验证建表调用
        assert mock_cursor.execute.call_count >= 2
        
        # 验证导入调用
        scraper.scrape_and_import_admissions()
        assert mock_cursor.executemany.called
        assert mock_conn.commit.called

    @patch('src.regulation_ingester.chromadb.PersistentClient')
    @patch('src.regulation_ingester.genai.embed_content')
    def test_regulation_ingester(self, mock_embed, mock_chroma):
        """测试 RegulationIngester 切片和向量入库流程"""
        mock_collection = MagicMock()
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
        
        # Mock embedding return
        mock_embed.return_value = {"embedding": [0.1] * 768}
        
        ingester = RegulationIngester(db_path=":memory:")
        
        # Test chunking
        chunks = ingester.chunk_text("A" * 1000, max_chunk_size=500, overlap=50)
        assert len(chunks) == 3
        
        # Test ingestion
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key"}):
            ingester.ingest_regulation("Test College", 2023, "Eyesight", "A" * 600)
            
            # Should have called embed_content
            assert mock_embed.called
            # Should have added to collection
            assert mock_collection.add.called

    @patch('src.audit.chromadb.PersistentClient')
    def test_automated_audit(self, mock_chroma):
        """测试 AutomatedAudit 风控排雷和飞书卡片生成流程"""
        mock_collection = MagicMock()
        mock_chroma.return_value.get_or_create_collection.return_value = mock_collection
        
        # Mock retrieval returning some eyesight restriction
        mock_collection.query.return_value = {
            "documents": [["该专业不招收色弱及色盲考生。英语成绩要求不低于110分。"]]
        }
        
        audit = AutomatedAudit(db_path=":memory:")
        
        # Test major audit with restrictions
        user_prof = {"english_score": 105, "eyesight_color": "Weak"}
        
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}): # Force heuristic fallback
            result = audit.audit_major(user_prof, "Test College", "Computer Science")
            
            # Check rejection based on eyesight
            assert result["status"] in ["Rejected", "High Risk"]
            
        # Test Feishu card generation
        recs = [{"college_name": "Test College", "major_name": "CS", "probability": 90}]
        card = audit.generate_feishu_card(recs, user_prof)
        
        assert card["msg_type"] == "interactive"
        assert "elements" in card["card"]
        assert len(card["card"]["elements"]) > 0
