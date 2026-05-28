# iTunes to Brennan JB7 Converter

A Python/tkinter application that converts an iTunes Music Library into the
hardfi format required by a Brennan JB7 audio player.

## Features

- Scans an iTunes Music directory (`Artist/Album/track` structure)
- Detects DRM-protected files using the mutagen library
- Shows a summary of file types (ALAC, AAC, MP3, FLAC, etc.) and DRM status
- Identifies albums with few tracks (configurable threshold)
- Identifies albums whose files do not start with track numbers
- Select specific artists and albums for processing
- Copies files to JB7-compatible directory structure (`Artist   Album/track`)
- Track order preserved via iTunes track numbering

## Requirements

- Python 3.8+
- Tkinter (included with Python on macOS, may need separate install on Linux)

## Setup

    make setup

Or manually:

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

## Usage

    make run

Or:

    python3 -m src.app

### Workflow

1. **Set source** – point to your iTunes Music folder
   (the directory containing `Artist/Album/track` structure)
2. **Set destination** – choose where JB7 output will be written
3. **Set threshold** – minimum tracks to consider something a full album
   (default 4)
4. **Scan Library** – analyse DRM status, file types, album sizes, and
   track numbering
5. **Review summary** – check DRM warnings, small albums, and albums
   without track numbers. Click the detail buttons for full lists.
6. **Select albums** – click individual albums to toggle, or use
   Select All / Deselect All. Click an artist name to toggle all
   its albums at once.
7. **Convert Selected** – after a confirmation dialog that lists any
   flagged items, files are copied into `Artist   Album/` directories.

## Testing

    make test

Run with coverage (requires >90%):

    make coverage

Coverage reports are written to the terminal and to `htmlcov/`.

## Cleanup

    make clean

Removes the virtual environment, `__pycache__` directories, and
coverage artifacts.
