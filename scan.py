import os
import re
from typing import List, Tuple, Optional
import requests
from db import add_movie, get_all_movies
from rich.prompt import Prompt, Confirm
from rich.console import Console
import json

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi")
console = Console()

# --- V4 TMDb Search ---
def tmdb_v4_search(query: str, bearer_token: str, language: str = "en-US", include_adult: bool = False, page: int = 1):
    url = "https://api.themoviedb.org/3/search/movie"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "accept": "application/json"
    }
    params = {
        "query": query,
        "include_adult": str(include_adult).lower(),
        "language": language,
        "page": page
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        console.print(f"[red]TMDb API error: {response.status_code} {response.text}[/red]")
        return []

def tmdb_v4_search_by_id(tmdb_id: str, bearer_token: str):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        console.print(f"[red]TMDb API error: {response.status_code} {response.text}[/red]")
        return None

def guess_title_year(filename: str) -> Tuple[str, Optional[int]]:
    # Remove bracketed/parenthetical info and common tags
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[\[\(].*?[\]\)]", "", name)  # Remove [brackets] and (parentheses)
    name = re.sub(r"[._-]", " ", name)  # Replace separators with space
    name = re.sub(r"\b(720p|1080p|2160p|x264|x265|h264|h265|bluray|bdrip|webrip|dvdrip|hdrip|subs?|ac3|dts|aac|ita|eng|spa|trilogia|fanart|poster|thumb)\b", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip()
    # Try to extract year
    match = re.search(r"(19|20)\d{2}", filename)
    year = int(match.group(0)) if match else None
    return name, year

def scan_directory(source_dir: str, tmdb_bearer_token: str):
    # Get already recorded files from the database
    recorded_files = {movie['absolute_path'] for movie in get_all_movies()}
    for root, _, files in os.walk(source_dir):
        console.print(f"[yellow]Scanning directory: {root} with {len(files)} files...[/yellow]")
        for file in files:
            abs_path = os.path.abspath(os.path.join(root, file))
            rel_path = os.path.relpath(abs_path, source_dir)
            if abs_path in recorded_files:
                console.print(f"[green]Skipping already recorded:[/green] {abs_path}")
                continue
            if file.lower().endswith(VIDEO_EXTENSIONS):
                console.print(f"[blue]Found video file:[/blue] {abs_path}")
                title_guess, year_guess = guess_title_year(file)
                console.print(f"\n[bold]File:[/bold] {abs_path}")
                console.print(f"Guessed: [cyan]{title_guess}[/cyan] ({year_guess or 'unknown year'})")

                # V4 Search
                while True:
                    results = tmdb_v4_search(title_guess, tmdb_bearer_token)
                    if results:
                        # Show top 3 results + option 0 for manual
                        for idx, m in enumerate(results[:3], start=1):
                            # Fetch extra details for each result (director, production)
                            details = tmdb_v4_search_by_id(m['id'], tmdb_bearer_token)
                            # Get production companies (first one or all)
                            prod = ''
                            if details and 'production_companies' in details and details['production_companies']:
                                prod = details['production_companies'][0]['name']
                            # Get director from credits if available
                            director = ''
                            if details and 'credits' in details and 'crew' in details['credits']:
                                for crew in details['credits']['crew']:
                                    if crew.get('job') == 'Director':
                                        director = crew.get('name')
                                        break
                            # Fallback: try to fetch credits if not present
                            if not director:
                                # Try to fetch credits endpoint
                                credits_url = f"https://api.themoviedb.org/3/movie/{m['id']}/credits"
                                headers = {"Authorization": f"Bearer {tmdb_bearer_token}", "accept": "application/json"}
                                credits_resp = requests.get(credits_url, headers=headers)
                                if credits_resp.status_code == 200:
                                    credits = credits_resp.json()
                                    for crew in credits.get('crew', []):
                                        if crew.get('job') == 'Director':
                                            director = crew.get('name')
                                            break
                            extra = f" | [magenta]{prod}[/magenta] | [green]{director}[/green]" if prod or director else ''
                            console.print(f"{idx}. {m['title']} ({m.get('release_date', '')[:4]}) [ID: {m['id']}] {extra}")
                        console.print("0. [Manual search or TMDb ID / Skip]")
                        choice = Prompt.ask("Select match (1-3), 0 for manual", default="1")
                        if choice == "0":
                            # Enter manual mode
                            console.print("[yellow]Manual mode:[/yellow]")
                            console.print("1. Propose a new search term")
                            console.print("2. Enter TMDb movie ID manually")
                            console.print("0. Skip this file")
                            manual_choice = Prompt.ask("Select option", default="1")
                            if manual_choice == "1":
                                title_guess = Prompt.ask("Enter new search term", default=title_guess)
                                continue  # Retry search with new term
                            elif manual_choice == "2":
                                tmdb_id = Prompt.ask("Enter TMDb movie ID", default="")
                                if tmdb_id.isdigit():
                                    movie = tmdb_v4_search_by_id(tmdb_id, tmdb_bearer_token)
                                    if not movie:
                                        console.print("[yellow]Invalid TMDb ID. Try again.")
                                        continue
                                    # Confirm
                                    confirm = Confirm.ask(f"Use: {movie['title']} ({movie.get('release_date', '')[:4]}) [ID: {movie['id']}]?", default=True)
                                    if not confirm:
                                        continue
                                    genres = ", ".join([g['name'] for g in movie.get('genres', [])]) if 'genres' in movie else ''
                                    metadata = json.dumps(movie, default=str)
                                    add_movie(abs_path, rel_path, movie['id'], movie['title'], int(movie.get('release_date', '0')[:4] or 0), genres, metadata)
                                    console.print("[green]Added to database.[/green]")
                                    break
                                else:
                                    console.print("[yellow]Invalid TMDb ID. Try again.")
                                    continue
                            elif manual_choice == "0":
                                console.print("[yellow]Skipping file.[/yellow]")
                                break
                            else:
                                continue
                        elif choice.isdigit() and 1 <= int(choice) <= len(results[:3]):
                            movie = results[int(choice)-1]
                            # Confirm
                            confirm = Confirm.ask(f"Use: {movie['title']} ({movie.get('release_date', '')[:4]}) [ID: {movie['id']}]?", default=True)
                            if not confirm:
                                continue
                            genres = ", ".join([g['name'] for g in movie.get('genres', [])]) if 'genres' in movie else ''
                            metadata = json.dumps(movie, default=str)
                            add_movie(abs_path, rel_path, movie['id'], movie['title'], int(movie.get('release_date', '0')[:4] or 0), genres, metadata)
                            console.print("[green]Added to database.[/green]")
                            break
                        else:
                            continue
                    else:
                        # No results found, go to manual mode
                        console.print("[red]No TMDb results found.[/red]")
                        console.print("[yellow]Manual mode:[/yellow]")
                        console.print("1. Propose a new search term")
                        console.print("2. Enter TMDb movie ID manually")
                        console.print("0. Skip this file")
                        manual_choice = Prompt.ask("Select option", default="1")
                        if manual_choice == "1":
                            title_guess = Prompt.ask("Enter new search term", default=title_guess)
                            continue  # Retry search with new term
                        elif manual_choice == "2":
                            tmdb_id = Prompt.ask("Enter TMDb movie ID", default="")
                            if tmdb_id.isdigit():
                                movie = tmdb_v4_search_by_id(tmdb_id, tmdb_bearer_token)
                                if not movie:
                                    console.print("[yellow]Invalid TMDb ID. Try again.")
                                    continue
                                # Confirm
                                confirm = Confirm.ask(f"Use: {movie['title']} ({movie.get('release_date', '')[:4]}) [ID: {movie['id']}]?", default=True)
                                if not confirm:
                                    continue
                                genres = ", ".join([g['name'] for g in movie.get('genres', [])]) if 'genres' in movie else ''
                                metadata = json.dumps(movie, default=str)
                                add_movie(abs_path, rel_path, movie['id'], movie['title'], int(movie.get('release_date', '0')[:4] or 0), genres, metadata)
                                console.print("[green]Added to database.[/green]")
                                break
                            else:
                                console.print("[yellow]Invalid TMDb ID. Try again.")
                                continue
                        elif manual_choice == "0":
                            console.print("[yellow]Skipping file.[/yellow]")
                            break
                        else:
                            continue
