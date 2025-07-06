import sqlite3
from typing import Optional, Dict, Any, List

DB_FILE = "movie_organiser.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            absolute_path TEXT PRIMARY KEY,
            tmdb_id INTEGER,
            title TEXT,
            year INTEGER,
            genres TEXT,
            metadata TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_movie(absolute_path: str, tmdb_id: int, title: str, year: int, genres: str, metadata: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO movies (absolute_path, tmdb_id, title, year, genres, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (absolute_path, tmdb_id, title, year, genres, metadata))
    conn.commit()
    conn.close()

def get_all_movies() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT absolute_path, tmdb_id, title, year, genres, metadata FROM movies')
    rows = c.fetchall()
    conn.close()
    return [
        {
            "absolute_path": row[0],
            "tmdb_id": row[1],
            "title": row[2],
            "year": row[3],
            "genres": row[4],
            "metadata": row[5]
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
