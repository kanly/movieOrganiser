import os
import sqlite3
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from db import DB_FILE, update_movie, set_skip_flag
from scan import tmdb_search_and_select

def human_size(size):
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"

def review_database():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT absolute_path, tmdb_id, title, skip FROM movies ORDER BY absolute_path")
    rows = c.fetchall()
    conn.close()

    console = Console()
    while True:
        table = Table(show_lines=True)
        table.add_column("#", width=4, justify="right")
        table.add_column("Filename", width=40, overflow="fold")
        table.add_column("TMDb Title (ID)", width=32, overflow="fold")
        table.add_column("File Size", width=10)
        table.add_column("Ignored", width=8)

        file_info = []
        for idx, (abs_path, tmdb_id, title, skip) in enumerate(rows):
            filename = os.path.basename(abs_path)
            try:
                size = os.path.getsize(abs_path)
                size_str = human_size(size)
            except Exception:
                size_str = "N/A"
            file_info.append((abs_path, tmdb_id, title, skip, size_str))
            table.add_row(
                str(idx+1),
                filename[:40],
                f"{title} ({tmdb_id})" if tmdb_id else "",
                size_str,
                "true" if skip else "false"
            )

        console.print(table)
        sel = IntPrompt.ask("Select a line to edit (0 to exit)", default=0)
        if sel == 0:
            break
        if not (1 <= sel <= len(file_info)):
            console.print("[red]Invalid selection.[/red]")
            continue

        abs_path, tmdb_id, title, skip, size_str = file_info[sel-1]
        console.print(f"\nEditing: [bold]{abs_path}[/bold]")
        action = Prompt.ask(
            "Action: [s]earch TMDb again, [t]oggle ignore, [q]uit",
            choices=["s", "t", "q"], default="q"
        )
        if action == "q":
            break
        elif action == "t":
            set_skip_flag(abs_path, not skip)
            console.print(f"[green]Ignore flag set to {not skip}.[/green]")
        elif action == "s":
            new_tmdb_id, new_title, new_year, new_genres, new_metadata = tmdb_search_and_select(os.path.basename(abs_path))
            if new_tmdb_id:
                update_movie(abs_path, tmdb_id=new_tmdb_id, title=new_title, year=new_year, genres=new_genres, metadata=new_metadata)
                console.print("[green]Movie info updated.[/green]")
        # Refresh data
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT absolute_path, tmdb_id, title, skip FROM movies ORDER BY absolute_path")
        rows = c.fetchall()
        conn.close()