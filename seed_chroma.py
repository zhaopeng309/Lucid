import os
import chromadb

def seed_chroma():
    db_path = 'data/chroma_db'
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="college_regulations")
    
    # Let's delete existing documents first to avoid duplicates
    try:
        # In Chroma, we can delete by metadata or IDs
        # To be safe, let's just delete the entire collection and recreate
        client.delete_collection(name="college_regulations")
        collection = client.get_or_create_collection(name="college_regulations")
    except Exception as e:
        print(f"Clean up collection failed: {e}")

    # Documents to insert
    documents = [
        "怀化学院招生章程：软件工程专业录取不限单科成绩。物理类考生高考选考科目必须包含物理和化学。学校对考生身体健康状况要求按教育部等部门联合印发的《普通高等学校招生体检工作指导意见》执行。无特殊视力限制。",
        "湖南软件职业技术大学2023年招生简章：计算机科学与技术专业为普通本科专业，学费为16000元/年。请家庭经济困难考生慎重报考。该专业不限男女比例，不设单科成绩最低限制。",
        "长沙民政职业技术学院招生章程：软件技术专业属于电子信息大类，本专业无视力色觉、单科分数等限制。面向物理类考生计划充足，服从调剂不退档。优秀高职毕业生可参加专升本考试录取到本科院校继续深造。"
    ]
    
    metadatas = [
        {"college_name": "怀化学院"},
        {"college_name": "湖南软件职业技术大学"},
        {"college_name": "长沙民政职业技术学院"}
    ]
    
    ids = [
        "hhxy_01",
        "hnrj_01",
        "csmz_01"
    ]
    
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Successfully seeded {len(documents)} regulations into ChromaDB.")

if __name__ == "__main__":
    seed_chroma()
