import os
import json
import re
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

def sanitize_folder_name(name):
    # Remove or replace problematic characters for Kodi and filesystems
    name = name.replace(':', '')  # Remove colons
    name = name.replace('?', '')  # Remove question marks
    name = name.replace('/', '-') # Replace slashes with dash
    name = name.replace('"', '') # Remove double quotes
    name = name.replace('|', '')  # Remove pipes
    name = name.replace('<', '')  # Remove less than
    name = name.replace('>', '')  # Remove greater than
    name = name.replace('*', '')  # Remove asterisks
    name = name.replace('\\', '') # Remove backslashes
    name = re.sub(r'\s+', ' ', name)  # Collapse multiple spaces
    name = name.strip()
    return name

def build_structure(target_dir: str, mode: Literal["title", "year"] = "title", dry_run: bool = False, script_path: str = None, source_root: str = None, effective_source_root: str = None):
    def bash_escape(path):
        # Escape single quotes for bash: ' -> '\''
        return "'" + path.replace("'", "'\\''") + "'"

    movies = get_all_movies()
    ln_commands = []
    mkdirs = set()
    for movie in movies:
        if movie.get("skip", False):
            continue
        # Use effective_source_root if provided, else fall back to source_root logic
        if script_path and effective_source_root:
            src = os.path.join(effective_source_root, movie["relative_path"])
        elif script_path and source_root:
            src = os.path.join(source_root, movie["relative_path"])
        else:
            src = movie["absolute_path"]
        title = movie["title"]
        year = movie["year"]
        if mode == "title":
            folder = sanitize_folder_name(f"{title} ({year})" if year else title)
        elif mode == "year":
            folder = str(year) if year else "Unknown"
        else:
            folder = sanitize_folder_name(title)
        dest_dir = os.path.join(target_dir, folder)
        # Use sanitized folder name as the symlink name (with extension from original file)
        ext = os.path.splitext(os.path.basename(src))[1]
        dest_link = os.path.join(dest_dir, f"{folder}{ext}")
        if script_path:
            mkdirs.add(dest_dir)
            ln_commands.append(f"ln -s {bash_escape(src)} {bash_escape(dest_link)}")
        else:
            os.makedirs(dest_dir, exist_ok=True)
            safe_symlink(src, dest_link, dry_run=dry_run)
    if script_path:
        with open(script_path, 'w') as f:
            f.write('#!/bin/bash\n')
            for d in sorted(mkdirs):
                f.write(f"mkdir -p {bash_escape(d)}\n")
            for cmd in ln_commands:
                f.write(cmd + '\n')
        console.print(f"[green]Bash script with mkdir and ln -s commands written to {script_path}[/green]")
