import re
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from .scanner import AlbumInfo, TrackInfo

DISC_PREFIX_RE = re.compile(r'^(\d+)-(\d+)\s')


def _parse_disc_prefix(filename: str) -> Tuple[Optional[int], str]:
    match = DISC_PREFIX_RE.match(filename)
    if match:
        disc_num = int(match.group(1))
        clean = filename[match.start(2):]
        return disc_num, clean
    return None, filename


def make_jb7_dirname(
    artist: str, album: str, disc_num: Optional[int] = None, suffix: str = "",
) -> str:
    base = f"{artist}   {album}"
    if disc_num is not None:
        base = f"{base} CD{disc_num}"
    if suffix:
        base = f"{base} {suffix}"
    return base.replace('_', '-')


def convert_album(
    album: AlbumInfo,
    dest_base: Path,
    progress_callback: Optional[Callable[[str], None]] = None,
    suffix: str = "",
) -> int:
    disc_tracks: Dict[Optional[int], List[Tuple[TrackInfo, str]]] = {}
    for track in album.tracks:
        disc_num, clean_name = _parse_disc_prefix(track.filename)
        clean_name = clean_name.replace('_', '-')
        disc_tracks.setdefault(disc_num, []).append((track, clean_name))

    copied = 0
    for disc_num, tracks in disc_tracks.items():
        jb7_dirname = make_jb7_dirname(album.artist, album.name, disc_num, suffix)
        dest_dir = dest_base / jb7_dirname
        dest_dir.mkdir(parents=True, exist_ok=True)

        for track, dest_name in tracks:
            src = Path(track.filepath)
            dest = dest_dir / dest_name

            if not src.exists():
                if progress_callback:
                    progress_callback(f"Source not found: {track.filename}")
                continue

            try:
                shutil.copy2(str(src), str(dest))
                copied += 1
                if progress_callback:
                    progress_callback(f"Copied: {dest_name}")
            except (IOError, OSError):
                try:
                    shutil.copy(str(src), str(dest))
                    copied += 1
                    if progress_callback:
                        progress_callback(f"Copied (no metadata): {dest_name}")
                except (IOError, OSError) as e2:
                    if progress_callback:
                        progress_callback(f"Error: {track.filename} - {e2}")

    return copied


def convert_selected(
    selected: Dict[str, Dict[str, AlbumInfo]],
    dest_dir: str,
    progress_callback: Optional[Callable[[str], None]] = None,
    suffix: str = "",
) -> int:
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    total = 0
    for artist, albums in selected.items():
        for album_name, album in albums.items():
            if progress_callback:
                progress_callback(f"Processing: {artist} / {album_name}")
            total += convert_album(album, dest_path, progress_callback, suffix)

    return total
