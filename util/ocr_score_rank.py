#!/usr/bin/env python
import os
import sys
import argparse
import csv
import io
import sqlite3
import pandas as pd
from PIL import Image
import google.generativeai as genai

def run_ocr(image_path: str) -> str:
    """
    Call Gemini's multimodal model to extract the tabular score/rank data from the image.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: Neither GEMINI_API_KEY nor GOOGLE_API_KEY environment variable is set.")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    # Use gemini-2.5-flash as it is highly efficient and reliable for multimodal tasks
    model_name = "gemini-2.5-flash"
    model = genai.GenerativeModel(model_name)
    
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image {image_path}: {e}")
        sys.exit(1)
        
    prompt = """You are an expert OCR and data extraction system.
Analyze the provided image which is a "一分一段表" (Score to Rank Mapping Table) from China's Gaokao (college entrance examination).
Extract the tabular data from the image. The table usually contains columns for:
1. Score (分数)
2. Number of students at this score (本分人数 / 人数)
3. Cumulative Rank (累计人数 / 累计位次)

Output the extracted data strictly in CSV format with the following header:
score,num_at_score,cumulative_rank

Rules:
1. Only output valid CSV data. Do not include markdown code block syntax (such as ```csv) or any conversational text in the final output. Just start directly with the CSV header.
2. Ensure every row has 3 columns: integer score, integer number of students, integer cumulative rank.
3. If there are multiple side-by-side sub-tables in the image (e.g. Columns 1-3 is one set, Columns 4-6 is another set), merge them vertically into a single sequential list sorted by score descending.
4. Do not miss any rows. Do not hallucinate scores.
"""
    
    try:
        response = model.generate_content([img, prompt])
        return response.text.strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(1)

def clean_csv_response(response_text: str) -> str:
    """
    Remove markdown code block wraps (like ```csv ... ```) if Gemini includes them.
    """
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned

def process_data(csv_text: str, province: str, year: int, category: str) -> pd.DataFrame:
    """
    Parse CSV, perform schema validation, and calculate rank_start / rank_end.
    """
    f = io.StringIO(csv_text)
    try:
        df = pd.read_csv(f)
    except Exception as e:
        print(f"Error parsing CSV text: {e}")
        print("Raw CSV text was:")
        print(csv_text)
        sys.exit(1)
        
    required_cols = ['score', 'num_at_score', 'cumulative_rank']
    
    # Auto-normalize and map fuzzy column names if needed
    df.columns = [c.lower().strip() for c in df.columns]
    mapping = {
        '分数': 'score', 'score': 'score',
        '人数': 'num_at_score', 'num_at_score': 'num_at_score', '本分人数': 'num_at_score', 'count': 'num_at_score',
        '累计人数': 'cumulative_rank', 'cumulative_rank': 'cumulative_rank', '累计位次': 'cumulative_rank'
    }
    
    mapped_cols = []
    for col_name in df.columns:
        if col_name in mapping:
            mapped_cols.append(mapping[col_name])
        else:
            mapped_cols.append(col_name)
    df.columns = mapped_cols
            
    for col in required_cols:
        if col not in df.columns:
            print(f"Error: Missing required column '{col}' in extracted data. Columns found: {df.columns.tolist()}")
            sys.exit(1)
            
    # Drop rows with missing values in required columns
    df = df.dropna(subset=required_cols)
    
    # Cast types safely
    try:
        df['score'] = df['score'].astype(float).astype(int)
        df['num_at_score'] = df['num_at_score'].astype(float).astype(int)
        df['cumulative_rank'] = df['cumulative_rank'].astype(float).astype(int)
    except Exception as e:
        print(f"Error converting data types to integer: {e}")
        sys.exit(1)
        
    # Build target columns
    df['year'] = year
    df['province'] = province
    df['category'] = category
    df['count'] = df['num_at_score']
    df['rank_end'] = df['cumulative_rank']
    # rank_start = rank_end - count + 1
    df['rank_start'] = df['rank_end'] - df['count'] + 1
    
    final_cols = ['year', 'province', 'category', 'score', 'rank_start', 'rank_end', 'count']
    return df[final_cols]

def import_to_db(df: pd.DataFrame, db_path: str):
    """
    Import the processed DataFrame into SQLite database.
    """
    # Put the project root and src directory into path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_root)
    sys.path.append(os.path.join(project_root, 'src'))
    
    try:
        from src.mapper import RankScoreMapper
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # Initialize RankScoreMapper with database path
        mapper = RankScoreMapper(db_path=db_path)
        
        # Clean existing records for same province, year, category to prevent duplicates/violations
        if not df.empty:
            sample_row = df.iloc[0]
            year = int(sample_row['year'])
            province = str(sample_row['province'])
            category = str(sample_row['category'])
            
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM one_mark_one_rank WHERE year=? AND province=? AND category=?",
                    (year, province, category)
                )
                conn.commit()
            finally:
                conn.close()
        
        mapper.import_data(df)
        print(f"Successfully imported {len(df)} records into 'one_mark_one_rank' table in {db_path}.")
    except Exception as e:
        print(f"Error during database import: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Lucid Gaokao Score-Rank Multi-modal OCR Utility")
    parser.add_argument("--image", required=True, help="Path to the score-rank table image")
    parser.add_argument("--province", required=True, help="Province name (e.g. Hunan, Zhejiang)")
    parser.add_argument("--year", required=True, type=int, help="Gaokao year (e.g. 2025)")
    parser.add_argument("--category", required=True, help="Candidate category (e.g. Physics, History, Comprehensive)")
    parser.add_argument("--output", help="Output path for the generated CSV file")
    parser.add_argument("--import-db", action="store_true", help="Automatically import the generated CSV into the SQLite database")
    parser.add_argument("--db-path", default="data/lucid.db", help="Path to the SQLite database file (default: data/lucid.db)")
    
    args = parser.parse_args()
    
    print(f"Starting OCR processing for image: {args.image}...")
    
    # 1. Run multi-modal OCR
    raw_response = run_ocr(args.image)
    
    # 2. Clean Gemini code blocks if any
    cleaned_csv = clean_csv_response(raw_response)
    
    # 3. Clean fields and calculate rank_start/rank_end
    df = process_data(cleaned_csv, args.province, args.year, args.category)
    
    # 4. Save to CSV
    output_path = args.output
    if not output_path:
        os.makedirs("data", exist_ok=True)
        output_path = f"data/score_rank_{args.province.lower()}_{args.year}_{args.category.lower()}.csv"
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"CSV data successfully written to: {output_path}")
    
    # 5. Optional DB import
    if args.import_db:
        print(f"Importing to SQLite database at {args.db_path}...")
        import_to_db(df, args.db_path)

if __name__ == "__main__":
    main()
