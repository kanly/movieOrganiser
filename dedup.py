import os
from db import get_all_movies, set_skip_flag
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

def human_readable_size(size):
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

def dedup():
    console = Console()
    movies = get_all_movies()
    # Group by tmdb_id
    from collections import defaultdict
    tmdb_groups = defaultdict(list)
    for m in movies:
        if m['tmdb_id']:
            tmdb_groups[m['tmdb_id']].append(m)
    for tmdb_id, group in tmdb_groups.items():
        if len(group) <= 1:
            continue
        console.print(f"\n[bold yellow]Duplicates for TMDb ID {tmdb_id} ({group[0]['title']})[/bold yellow]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#")
        table.add_column("File name")
        table.add_column("Size")
        for idx, m in enumerate(group):
            try:
                size = os.path.getsize(m['absolute_path'])
                size_str = human_readable_size(size)
            except Exception:
                size_str = "?"
            table.add_row(str(idx+1), os.path.basename(m['absolute_path']), size_str)
        console.print(table)
        choice = Prompt.ask(f"Pick the file to keep (1-{len(group)})", default="1")
        try:
            keep_idx = int(choice) - 1
            if not (0 <= keep_idx < len(group)):
                raise ValueError
        except Exception:
            console.print("[red]Invalid choice, skipping group.[/red]")
            continue
        for idx, m in enumerate(group):
            set_skip_flag(m['absolute_path'], skip=(idx != keep_idx))
        console.print(f"[green]Marked all but one file to be skipped for TMDb ID {tmdb_id}.[/green]")
