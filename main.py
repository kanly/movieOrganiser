import typer
from db import init_db, reset_db
from scan import scan_directory
from build import build_structure

app = typer.Typer(help="Movie Organiser CLI")

@app.command()
def scan(
    source_dir: str = typer.Argument(..., help="Directory to scan for movie files"),
    tmdb_bearer_token: str = typer.Option(..., prompt=True, hide_input=True, help="TMDb V4 Bearer Token")
):
    """Scan directory and build movie database using TMDb v4 API (Bearer token)."""
    init_db()
    scan_directory(source_dir, tmdb_bearer_token)

@app.command()
def build(
    target_dir: str = typer.Argument(..., help="Directory to create symlinked structure"),
    mode: str = typer.Option("title", help="Folder structure: 'title' or 'year'"),
    dry_run: bool = typer.Option(False, help="Preview changes without making them"),
    script: str = typer.Option(None, help="Path to bash script to write ln -s commands instead of executing them")
):
    """Build symlinked movie structure from database or generate a bash script."""
    build_structure(target_dir, mode=mode, dry_run=dry_run, script_path=script)

@app.command()
def reset():
    """Reset the movie database."""
    reset_db()
    typer.echo("Database reset.")

if __name__ == "__main__":
    app()
