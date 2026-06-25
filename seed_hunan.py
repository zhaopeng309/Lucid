import sqlite3

def seed():
    conn = sqlite3.connect('data/lucid.db')
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='college_admissions'")
    if not cursor.fetchone():
        print("Table 'college_admissions' does not exist yet. Please run scraper.py first.")
        conn.close()
        return

    # Delete existing Hunan records if any to avoid duplication
    cursor.execute("DELETE FROM college_admissions WHERE province='Hunan'")
    
    hunan_admissions = [
        # Reach (15% - 45%): min_rank slightly higher than candidate rank 200,000 (e.g. 175,000 - 190,000)
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '10543', 'college_name': '湖南工学院', 'college_tags': '公办,普通本科',
            'city': 'Hengyang', 'major_code': '080202', 'major_name': '机械设计制造及其自动化',
            'plan_count': 15, 'min_score': 468, 'min_rank': 175000, 'tuition': 4500
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '10553', 'college_name': '湖南城市学院', 'college_tags': '公办,普通本科',
            'city': 'Yiyang', 'major_code': '081001', 'major_name': '土木工程',
            'plan_count': 12, 'min_score': 462, 'min_rank': 185000, 'tuition': 4800
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '11527', 'college_name': '邵阳学院', 'college_tags': '公办,普通本科',
            'city': 'Shaoyang', 'major_code': '080901', 'major_name': '计算机科学与技术',
            'plan_count': 20, 'min_score': 458, 'min_rank': 192000, 'tuition': 5000
        },
        
        # Match (45% - 75%): min_rank around 195,000 - 210,000 (candidate at 200,000)
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '10548', 'college_name': '怀化学院', 'college_tags': '公办,普通本科',
            'city': 'Huaihua', 'major_code': '080902', 'major_name': '软件工程',
            'plan_count': 25, 'min_score': 451, 'min_rank': 202000, 'tuition': 5500
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '12345', 'college_name': '湖南软件职业技术大学', 'college_tags': '民办,职业本科',
            'city': 'Xiangtan', 'major_code': '080901', 'major_name': '计算机科学与技术',
            'plan_count': 30, 'min_score': 448, 'min_rank': 208000, 'tuition': 16000
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '10555', 'college_name': '湘南学院', 'college_tags': '公办,普通本科',
            'city': 'Chenzhou', 'major_code': '080903', 'major_name': '网络工程',
            'plan_count': 18, 'min_score': 452, 'min_rank': 199000, 'tuition': 4800
        },
        
        # Safety (75% - 95%): min_rank 210,000 - 230,000
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '12845', 'college_name': '长沙民政职业技术学院', 'college_tags': '公办,国家示范高职',
            'city': 'Changsha', 'major_code': '610201', 'major_name': '软件技术',
            'plan_count': 50, 'min_score': 438, 'min_rank': 222000, 'tuition': 4600
        },
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '13045', 'college_name': '湖南铁道职业技术学院', 'college_tags': '公办,示范高职',
            'city': 'Zhuzhou', 'major_code': '600111', 'major_name': '铁道机车车辆',
            'plan_count': 40, 'min_score': 435, 'min_rank': 228000, 'tuition': 4500
        },
        
        # Fall-back (>=95%): min_rank > 230,000
        {
            'province': 'Hunan', 'year': 2023, 'category': 'Physics',
            'college_code': '13935', 'college_name': '湖南信息职业技术学院', 'college_tags': '公办,高职专科',
            'city': 'Changsha', 'major_code': '610202', 'major_name': '计算机应用技术',
            'plan_count': 35, 'min_score': 420, 'min_rank': 245000, 'tuition': 3500
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
        for r in hunan_admissions
    ]
    
    cursor.executemany(insert_query, tuples_to_insert)
    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(hunan_admissions)} Hunan physics admissions records.")

if __name__ == "__main__":
    seed()
