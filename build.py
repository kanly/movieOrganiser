import os
import json
from typing import Literal
from db import get_all_movies
from rich.console import Console

console = Console()

def safe_symlink(src, dst, dry_run=False):
    if os.path.exists(dst):
        if os.path.islink(dst) and os.readlink(dst) == src:
            return  # Already correct
        else:
            console.print(f"[yellow]Collision: {dst} exists. Skipping.[/yellow]")
            return
    if dry_run:
        console.print(f"[cyan]Would link:[/cyan] {dst} -> {src}")
    else:
        os.symlink(src, dst)
        console.print(f"[green]Linked:[/green] {dst} -> {src}")

def build_structure(target_dir: str, mode: Literal["title", "year"] = "title", dry_run: bool = False, script_path: str = None):
    movies = get_all_movies()
    ln_commands = []
    for movie in movies:
        src = movie["absolute_path"]
        title = movie["title"]
        year = movie["year"]
        # Structure: target_dir/Title (Year)/original_filename
        if mode == "title":
            folder = f"{title} ({year})" if year else title
        elif mode == "year":
            folder = str(year) if year else "Unknown"
        else:
            folder = title
        dest_dir = os.path.join(target_dir, folder)
        os.makedirs(dest_dir, exist_ok=True)
        dest_link = os.path.join(dest_dir, os.path.basename(src))
        if script_path:
            ln_commands.append(f"ln -s '{src}' '{dest_link}'")
        else:
            safe_symlink(src, dest_link, dry_run=dry_run)
    if script_path:
        with open(script_path, 'w') as f:
            f.write('#!/bin/bash\n')
            for cmd in ln_commands:
                f.write(cmd + '\n')
        console.print(f"[green]Bash script with ln -s commands written to {script_path}[/green]")
