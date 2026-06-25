import sqlite3
import os
import chromadb

def seed_western_db():
    conn = sqlite3.connect('data/lucid.db')
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='college_admissions'")
    if not cursor.fetchone():
        print("Table 'college_admissions' does not exist yet.")
        conn.close()
        return

    # Delete existing Western records if any to avoid duplication
    cursor.execute("DELETE FROM college_admissions WHERE city IN ('Chengdu', 'Chongqing', 'Xi''an', 'Guiyang', 'Kunming', 'Lanzhou')")
    
    western_admissions = [
        # Reach (15% - 45%): min_rank slightly higher than candidate rank 200,000 (e.g. 175,000 - 190,000)
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '10622', 'college_name': '四川轻化工大学', 'college_tags': '公办,普通本科',
            'city': 'Chengdu', 'major_code': '080901', 'major_name': '计算机科学与技术',
            'plan_count': 8, 'min_score': 467, 'min_rank': 177000, 'tuition': 4800
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '11551', 'college_name': '重庆科技大学', 'college_tags': '公办,普通本科',
            'city': 'Chongqing', 'major_code': '080902', 'major_name': '软件工程',
            'plan_count': 10, 'min_score': 464, 'min_rank': 182000, 'tuition': 5500
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '11025', 'college_name': '西安文理学院', 'college_tags': '公办,普通本科',
            'city': 'Xi\'an', 'major_code': '080903', 'major_name': '网络工程',
            'plan_count': 5, 'min_score': 460, 'min_rank': 189000, 'tuition': 4500
        },
        
        # Match (45% - 75%): min_rank around 195,000 - 210,000 (candidate at 200,000)
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '11390', 'college_name': '昆明学院', 'college_tags': '公办,普通本科',
            'city': 'Kunming', 'major_code': '080901', 'major_name': '计算机科学与技术',
            'plan_count': 12, 'min_score': 453, 'min_rank': 198000, 'tuition': 4500
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '10662', 'college_name': '贵州中医药大学', 'college_tags': '公办,普通本科',
            'city': 'Guiyang', 'major_code': '100801', 'major_name': '中药学',
            'plan_count': 15, 'min_score': 450, 'min_rank': 203000, 'tuition': 5000
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '13110', 'college_name': '兰州资源环境职业技术大学', 'college_tags': '公办,职业本科',
            'city': 'Lanzhou', 'major_code': '080902', 'major_name': '软件工程技术',
            'plan_count': 14, 'min_score': 449, 'min_rank': 205000, 'tuition': 5500
        },
        
        # Safety (75% - 95%): min_rank 210,000 - 230,000
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '12756', 'college_name': '重庆工业职业技术学院', 'college_tags': '公办,国家示范高职',
            'city': 'Chongqing', 'major_code': '610201', 'major_name': '软件技术',
            'plan_count': 25, 'min_score': 439, 'min_rank': 221000, 'tuition': 4500
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '12518', 'college_name': '四川建筑职业技术学院', 'college_tags': '公办,示范高职',
            'city': 'Chengdu', 'major_code': '600201', 'major_name': '建筑工程技术',
            'plan_count': 30, 'min_score': 434, 'min_rank': 230000, 'tuition': 4100
        }
    ]

    insert_query = '''
        INSERT INTO college_admissions (
            province, year, category, college_code, college_name,
            college_tags, city, major_code, major_name, plan_count,
            min_score, min_rank, tuition
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    tuples_to_insert = [
        (
            r['province'], r['year'], r['category'], r['college_code'], r['college_name'],
            r['college_tags'], r['city'], r['major_code'], r['major_name'], r['plan_count'],
            r['min_score'], r['min_rank'], r['tuition']
        )
        for r in western_admissions
    ]
    
    cursor.executemany(insert_query, tuples_to_insert)
    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(western_admissions)} Western admissions records in SQLite.")


def seed_western_chroma():
    db_path = 'data/chroma_db'
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name="college_regulations")
    
    # We can just add additional documents
    documents = [
        "重庆科技大学招生简章：软件工程专业学费为5500元/年。要求物理类考生选科必须包含物理与化学，对英语单科不设最低分数拦截线。视力色觉要求符合教育部规定，无色盲色弱即可。",
        "昆明学院2023年招生章程：计算机科学与技术专业为普通公办本科专业。学校对考生单科成绩无特殊要求，体检执行教育部体检意见，色弱、色盲限报医学及艺术大类，计算机科学专业无特殊视力限制。",
        "贵州中医药大学招生章程：中药学专业为公办本科专业，对考生视力有严格要求，色盲、色弱者一律不予录取。请视力异常考生填报时予以避让。",
        "重庆工业职业技术学院招生简章：软件技术大类属于电子信息工程学院，不限单科成绩。对于色盲考生，电子信息类专业建议慎重报考，但软件技术无硬性体检拦截规则。"
    ]
    
    metadatas = [
        {"college_name": "重庆科技大学"},
        {"college_name": "昆明学院"},
        {"college_name": "贵州中医药大学"},
        {"college_name": "重庆工业职业技术学院"}
    ]
    
    ids = [
        "cqkj_01",
        "kmxy_01",
        "gzyy_01",
        "cqgy_01"
    ]
    
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(f"Successfully seeded {len(documents)} Western regulations into ChromaDB.")


if __name__ == "__main__":
    seed_western_db()
    seed_western_chroma()
