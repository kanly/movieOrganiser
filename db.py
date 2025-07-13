import sqlite3
from typing import Optional, Dict, Any, List

DB_FILE = "movie_organiser.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            absolute_path TEXT PRIMARY KEY,
            relative_path TEXT,
            tmdb_id INTEGER,
            title TEXT,
            year INTEGER,
            genres TEXT,
            metadata TEXT,
            skip INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_movie(absolute_path: str, relative_path: str, tmdb_id: int, title: str, year: int, genres: str, metadata: str, skip: int = 0):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO movies (absolute_path, relative_path, tmdb_id, title, year, genres, metadata, skip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (absolute_path, relative_path, tmdb_id, title, year, genres, metadata, skip))
    conn.commit()
    conn.close()

def get_all_movies() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT absolute_path, relative_path, tmdb_id, title, year, genres, metadata, skip FROM movies')
    rows = c.fetchall()
    conn.close()
    return [
        {
            "absolute_path": row[0],
            "relative_path": row[1],
            "tmdb_id": row[2],
            "title": row[3],
            "year": row[4],
            "genres": row[5],
            "metadata": row[6],
            "skip": bool(row[7])
        }
        for row in rows
    ]

def reset_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS movies')
    conn.commit()
    conn.close()
    init_db()

def set_skip_flag(absolute_path: str, skip: bool):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE movies SET skip = ? WHERE absolute_path = ?', (1 if skip else 0, absolute_path))
    conn.commit()
    conn.close()

def update_movie(absolute_path: str, **kwargs):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    fields = []
    values = []
    for k, v in kwargs.items():
        fields.append(f"{k}=?")
        values.append(v)
    values.append(absolute_path)
    c.execute(f"UPDATE movies SET {', '.join(fields)} WHERE absolute_path=?", values)
    conn.commit()
    conn.close()
