import os
import re
from typing import List, Tuple, Optional
from tmdbv3api import TMDb, Movie
from db import add_movie
from rich.prompt import Prompt, Confirm
from rich.console import Console
import json

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi")
console = Console()

def guess_title_year(filename: str) -> Tuple[str, Optional[int]]:
    # Simple regex: "Title (Year)" or "Title.Year"
    match = re.match(r"(.+?)[\.\s\(\[](d{4})[\)\]\.\s]", filename)
    if match:
        title = match.group(1).replace('.', ' ').replace('_', ' ').strip()
        year = int(match.group(2))
        return title, year
    # Fallback: remove extension, no year
    title = os.path.splitext(filename)[0].replace('.', ' ').replace('_', ' ').strip()
    return title, None

def scan_directory(source_dir: str, tmdb_api_key: str):
    tmdb = TMDb()
    tmdb.api_key = tmdb_api_key
    movie_api = Movie()

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(VIDEO_EXTENSIONS):
                abs_path = os.path.abspath(os.path.join(root, file))
                title_guess, year_guess = guess_title_year(file)
                console.print(f"\n[bold]File:[/bold] {abs_path}")
                console.print(f"Guessed: [cyan]{title_guess}[/cyan] ({year_guess or 'unknown year'})")

                # Search TMDb
                results = movie_api.search(title_guess)
                # Fix: Ensure results is a list
                if not isinstance(results, list) or not results:
                    console.print("[red]No TMDb results found.[/red]")
                    tmdb_id = Prompt.ask("Enter TMDb movie ID manually", default="")
                    if tmdb_id.isdigit():
                        movie = movie_api.details(int(tmdb_id))
                    else:
                        console.print("[yellow]Skipping file.[/yellow]")
                        continue
                else:
                    # Show top 3 results
                    for idx, m in enumerate(results[:3]):
                        console.print(f"{idx+1}. {m.title} ({getattr(m, 'release_date', '')[:4]}) [ID: {m.id}]")
                    choice = Prompt.ask("Select match (1-3), [s]kip, or enter TMDb ID", default="1")
                    if choice.isdigit() and 1 <= int(choice) <= len(results[:3]):
                        movie = results[int(choice)-1]
                    elif choice.isdigit():
                        movie = movie_api.details(int(choice))
                    else:
                        console.print("[yellow]Skipping file.[/yellow]")
                        continue

                # Confirm
                confirm = Confirm.ask(f"Use: {movie.title} ({getattr(movie, 'release_date', '')[:4]}) [ID: {movie.id}]?", default=True)
                if not confirm:
                    console.print("[yellow]Skipping file.[/yellow]")
                    continue

                genres = ", ".join([g['name'] for g in getattr(movie, 'genres', [])])
                metadata = json.dumps(movie.__dict__, default=str)
                add_movie(abs_path, movie.id, movie.title, int(getattr(movie, 'release_date', '0')[:4] or 0), genres, metadata)
                console.print("[green]Added to database.[/green]")
