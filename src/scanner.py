import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from mutagen.mp4 import MP4


SUPPORTED_EXTENSIONS = {
    '.mp3', '.m4a', '.m4p', '.mp4', '.flac',
    '.aiff', '.aif', '.wav', '.wma', '.ogg',
}


@dataclass
class TrackInfo:
    filename: str
    filepath: str
    file_type: str
    drm_protected: bool
    has_track_number: bool
    size_bytes: int


@dataclass
class AlbumInfo:
    name: str
    artist: str
    tracks: List[TrackInfo]
    min_tracks: int = 4

    @property
    def track_count_ok(self) -> bool:
        return len(self.tracks) >= self.min_tracks

    @property
    def has_track_numbers(self) -> bool:
        if not self.tracks:
            return False
        return all(t.has_track_number for t in self.tracks)

    @property
    def has_drm(self) -> bool:
        return any(t.drm_protected for t in self.tracks)


@dataclass
class ScanResult:
    artists: Dict[str, Dict[str, AlbumInfo]]
    total_files: int
    file_types: Dict[str, int]
    drm_free: Dict[str, int]
    drm_protected: Dict[str, int]
    small_albums: List[AlbumInfo]
    untracked_albums: List[AlbumInfo]
    protected_albums: List[AlbumInfo]


def _detect_m4a_codec(filepath: str) -> str:
    try:
        audio = MP4(filepath)
        codec = getattr(audio.info, 'codec', None) or ''
        if 'ALAC' in codec.upper():
            return 'ALAC'
        desc = getattr(audio.info, 'codec_description', None) or ''
        if 'ALAC' in desc.upper():
            return 'ALAC'
        return 'AAC'
    except Exception:
        return 'AAC'


def get_file_type(filepath: str) -> str:
    ext = Path(filepath).suffix.lower()
    if ext == '.mp3':
        return 'MP3'
    elif ext == '.m4p':
        return 'AAC (protected)'
    elif ext in ('.m4a', '.mp4'):
        return _detect_m4a_codec(filepath)
    elif ext == '.flac':
        return 'FLAC'
    elif ext in ('.aiff', '.aif'):
        return 'AIFF'
    elif ext == '.wav':
        return 'WAV'
    elif ext == '.wma':
        return 'WMA'
    elif ext == '.ogg':
        return 'OGG'
    return 'Unknown'


def check_drm(filepath: str) -> bool:
    ext = Path(filepath).suffix.lower()
    if ext == '.m4p':
        return True
    if ext in ('.m4a', '.mp4'):
        try:
            audio = MP4(filepath)
            _ = audio.info
            _ = audio.tags
            return False
        except Exception:
            return True
    return False


def has_track_number(filename: str) -> bool:
    stem = Path(filename).stem
    if not stem or not stem[0].isdigit():
        return False
    i = 0
    while i < len(stem) and stem[i].isdigit():
        i += 1
    if i == len(stem):
        return False
    return stem[i] in (' ', '.', '-', '_', ')')


def scan_directory(source_dir: str, min_tracks: int = 4) -> ScanResult:
    source_path = Path(source_dir)

    artists: Dict[str, Dict[str, AlbumInfo]] = {}
    total_files = 0
    file_types: Dict[str, int] = {}
    drm_free: Dict[str, int] = {}
    drm_protected: Dict[str, int] = {}

    if not source_path.is_dir():
        return ScanResult({}, 0, {}, {}, {}, [], [], [])

    for artist_dir in sorted(source_path.iterdir()):
        if not artist_dir.is_dir() or artist_dir.name.startswith('.'):
            continue
        artist_name = artist_dir.name
        artists[artist_name] = {}

        for album_dir in sorted(artist_dir.iterdir()):
            if not album_dir.is_dir() or album_dir.name.startswith('.'):
                continue
            album_name = album_dir.name
            tracks: List[TrackInfo] = []

            for track_file in sorted(album_dir.iterdir()):
                if not track_file.is_file():
                    continue
                if track_file.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue

                total_files += 1
                ftype = get_file_type(str(track_file))
                drm = check_drm(str(track_file))

                file_types[ftype] = file_types.get(ftype, 0) + 1
                if drm:
                    drm_protected[ftype] = drm_protected.get(ftype, 0) + 1
                else:
                    drm_free[ftype] = drm_free.get(ftype, 0) + 1

                try:
                    fsize = track_file.stat().st_size
                except OSError:
                    fsize = 0

                track = TrackInfo(
                    filename=track_file.name,
                    filepath=str(track_file.resolve()),
                    file_type=ftype,
                    drm_protected=drm,
                    has_track_number=has_track_number(track_file.name),
                    size_bytes=fsize,
                )
                tracks.append(track)

            if tracks:
                album = AlbumInfo(
                    name=album_name,
                    artist=artist_name,
                    tracks=tracks,
                    min_tracks=min_tracks,
                )
                artists[artist_name][album_name] = album

    all_albums = [
        album for artist_albums in artists.values()
        for album in artist_albums.values()
    ]
    small_albums = [a for a in all_albums if not a.track_count_ok]
    untracked_albums = [a for a in all_albums if not a.has_track_numbers]
    protected_albums = [a for a in all_albums if a.has_drm]

    return ScanResult(
        artists=artists,
        total_files=total_files,
        file_types=file_types,
        drm_free=drm_free,
        drm_protected=drm_protected,
        small_albums=small_albums,
        untracked_albums=untracked_albums,
        protected_albums=protected_albums,
    )
