import shutil
from pathlib import Path
from typing import Callable, Dict, Optional

from .scanner import AlbumInfo


def make_jb7_dirname(artist: str, album: str) -> str:
    return f"{artist}   {album}"


def convert_album(
    album: AlbumInfo,
    dest_base: Path,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> int:
    jb7_dirname = make_jb7_dirname(album.artist, album.name)
    dest_dir = dest_base / jb7_dirname
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for track in album.tracks:
        src = Path(track.filepath)
        dest = dest_dir / track.filename

        if not src.exists():
            if progress_callback:
                progress_callback(f"Source not found: {track.filename}")
            continue

        try:
            shutil.copy2(str(src), str(dest))
            copied += 1
            if progress_callback:
                progress_callback(f"Copied: {track.filename}")
        except (IOError, OSError) as e:
            if progress_callback:
                progress_callback(f"Error: {track.filename} - {e}")

    return copied


def convert_selected(
    selected: Dict[str, Dict[str, AlbumInfo]],
    dest_dir: str,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> int:
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    total = 0
    for artist, albums in selected.items():
        for album_name, album in albums.items():
            if progress_callback:
                progress_callback(f"Processing: {artist} / {album_name}")
            total += convert_album(album, dest_path, progress_callback)

    return total
