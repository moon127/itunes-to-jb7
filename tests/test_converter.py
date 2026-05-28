import os
from pathlib import Path

from src.converter import make_jb7_dirname, convert_album, convert_selected
from src.scanner import TrackInfo, AlbumInfo


class TestMakeJB7Dirname:
    def test_basic(self):
        assert make_jb7_dirname("Artist", "Album") == "Artist   Album"

    def test_with_spaces(self):
        assert make_jb7_dirname("Test Artist", "Test Album") == "Test Artist   Test Album"

    def test_single_names(self):
        assert make_jb7_dirname("A", "B") == "A   B"

    def test_special_chars(self):
        assert make_jb7_dirname("Artist/Name", "Album:1") == "Artist/Name   Album:1"


class TestConvertAlbum:
    def test_basic_copy(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        (src_dir / "01 Track.mp3").write_bytes(b"audio data 1")
        (src_dir / "02 Track.mp3").write_bytes(b"audio data 2")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo(
                "01 Track.mp3",
                str(src_dir / "01 Track.mp3"),
                "MP3", False, True, 11,
            ),
            TrackInfo(
                "02 Track.mp3",
                str(src_dir / "02 Track.mp3"),
                "MP3", False, True, 11,
            ),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        count = convert_album(album, dest_dir)
        assert count == 2

        jb7_dir = dest_dir / "Artist   Album"
        assert (jb7_dir / "01 Track.mp3").exists()
        assert (jb7_dir / "02 Track.mp3").exists()
        assert (jb7_dir / "01 Track.mp3").read_bytes() == b"audio data 1"
        assert (jb7_dir / "02 Track.mp3").read_bytes() == b"audio data 2"

    def test_missing_source_file(self, tmp_path):
        dest_dir = tmp_path / "dest"
        tracks = [
            TrackInfo(
                "missing.mp3",
                str(tmp_path / "nonexistent" / "missing.mp3"),
                "MP3", False, True, 0,
            ),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        count = convert_album(album, dest_dir)
        assert count == 0

        jb7_dir = dest_dir / "Artist   Album"
        assert jb7_dir.exists()

    def test_missing_source_with_callback(self, tmp_path):
        dest_dir = tmp_path / "dest"
        tracks = [
            TrackInfo(
                "gone.mp3",
                str(tmp_path / "nowhere" / "gone.mp3"),
                "MP3", False, True, 0,
            ),
        ]
        album = AlbumInfo("Album", "Artist", tracks)
        messages = []

        def cb(msg):
            messages.append(msg)

        count = convert_album(album, dest_dir, cb)
        assert count == 0
        assert any("Source not found" in m for m in messages)
        assert any("gone.mp3" in m for m in messages)

    def test_io_error(self, tmp_path, monkeypatch):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        test_file = src_dir / "01 Track.mp3"
        test_file.write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        def mock_copy2(*args, **kwargs):
            raise IOError("Disk full")

        monkeypatch.setattr("shutil.copy2", mock_copy2)

        tracks = [
            TrackInfo(
                "01 Track.mp3",
                str(test_file),
                "MP3", False, True, 4,
            ),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        count = convert_album(album, dest_dir)
        assert count == 0

    def test_io_error_with_callback(self, tmp_path, monkeypatch):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        test_file = src_dir / "01 Track.mp3"
        test_file.write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        def mock_copy2(*args, **kwargs):
            raise IOError("Disk full")

        monkeypatch.setattr("shutil.copy2", mock_copy2)

        tracks = [
            TrackInfo(
                "01 Track.mp3",
                str(test_file),
                "MP3", False, True, 4,
            ),
        ]
        album = AlbumInfo("Album", "Artist", tracks)
        messages = []

        def cb(msg):
            messages.append(msg)

        count = convert_album(album, dest_dir, cb)
        assert count == 0
        assert any("Error" in m for m in messages)
        assert any("Disk full" in m for m in messages)

    def test_callback_invoked(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        (src_dir / "01 Track.mp3").write_bytes(b"data")
        (src_dir / "02 Track.mp3").write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("01 Track.mp3", str(src_dir / "01 Track.mp3"), "MP3", False, True, 4),
            TrackInfo("02 Track.mp3", str(src_dir / "02 Track.mp3"), "MP3", False, True, 4),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        messages = []

        def cb(msg):
            messages.append(msg)

        count = convert_album(album, dest_dir, cb)
        assert count == 2
        assert len(messages) == 2
        assert "Copied: 01 Track.mp3" in messages
        assert "Copied: 02 Track.mp3" in messages

    def test_empty_tracks(self, tmp_path):
        dest_dir = tmp_path / "dest"
        album = AlbumInfo("Album", "Artist", [])

        count = convert_album(album, dest_dir)
        assert count == 0

        jb7_dir = dest_dir / "Artist   Album"
        assert jb7_dir.exists()

    def test_multiple_formats(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        (src_dir / "01 T.mp3").write_bytes(b"mp3")
        (src_dir / "02 T.flac").write_bytes(b"flac")
        (src_dir / "03 T.m4a").write_bytes(b"m4a")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("01 T.mp3", str(src_dir / "01 T.mp3"), "MP3", False, True, 3),
            TrackInfo("02 T.flac", str(src_dir / "02 T.flac"), "FLAC", False, True, 4),
            TrackInfo("03 T.m4a", str(src_dir / "03 T.m4a"), "AAC", False, True, 3),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        count = convert_album(album, dest_dir)
        assert count == 3

        jb7_dir = dest_dir / "Artist   Album"
        assert (jb7_dir / "01 T.mp3").read_bytes() == b"mp3"
        assert (jb7_dir / "02 T.flac").read_bytes() == b"flac"
        assert (jb7_dir / "03 T.m4a").read_bytes() == b"m4a"


class TestConvertSelected:
    def test_multiple_albums(self, tmp_path):
        src_dir = tmp_path / "src"
        d1 = src_dir / "Artist A" / "Album 1"
        d1.mkdir(parents=True)
        (d1 / "01 T.mp3").write_bytes(b"d1")
        d2 = src_dir / "Artist A" / "Album 2"
        d2.mkdir(parents=True)
        (d2 / "01 T.mp3").write_bytes(b"d2")
        d3 = src_dir / "Artist B" / "Album 1"
        d3.mkdir(parents=True)
        (d3 / "01 T.mp3").write_bytes(b"d3")

        a1 = AlbumInfo("Album 1", "Artist A", [
            TrackInfo("01 T.mp3", str(d1 / "01 T.mp3"), "MP3", False, True, 2),
        ])
        a2 = AlbumInfo("Album 2", "Artist A", [
            TrackInfo("01 T.mp3", str(d2 / "01 T.mp3"), "MP3", False, True, 2),
        ])
        a3 = AlbumInfo("Album 1", "Artist B", [
            TrackInfo("01 T.mp3", str(d3 / "01 T.mp3"), "MP3", False, True, 2),
        ])

        selected = {
            "Artist A": {"Album 1": a1, "Album 2": a2},
            "Artist B": {"Album 1": a3},
        }
        dest_dir = tmp_path / "dest"

        total = convert_selected(selected, str(dest_dir))
        assert total == 3

        assert (dest_dir / "Artist A   Album 1" / "01 T.mp3").exists()
        assert (dest_dir / "Artist A   Album 2" / "01 T.mp3").exists()
        assert (dest_dir / "Artist B   Album 1" / "01 T.mp3").exists()

    def test_empty_selection(self, tmp_path):
        dest_dir = tmp_path / "dest"
        total = convert_selected({}, str(dest_dir))
        assert total == 0
        assert dest_dir.exists()

    def test_callback_with_multiple(self, tmp_path):
        src_dir = tmp_path / "src"
        d = src_dir / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 T.mp3").write_bytes(b"d")
        (d / "02 T.mp3").write_bytes(b"d")

        album = AlbumInfo("Album", "Artist", [
            TrackInfo("01 T.mp3", str(d / "01 T.mp3"), "MP3", False, True, 1),
            TrackInfo("02 T.mp3", str(d / "02 T.mp3"), "MP3", False, True, 1),
        ])
        selected = {"Artist": {"Album": album}}
        dest_dir = tmp_path / "dest"

        messages = []

        def cb(msg):
            messages.append(msg)

        total = convert_selected(selected, str(dest_dir), cb)
        assert total == 2
        assert any("Processing: Artist / Album" in m for m in messages)
        assert any("Copied: 01 T.mp3" in m for m in messages)
        assert any("Copied: 02 T.mp3" in m for m in messages)

    def test_preserves_metadata(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        test_file = src_dir / "01 Track.mp3"
        test_file.write_bytes(b"audio data")
        import time
        orig_mtime = time.time() - 3600
        os.utime(str(test_file), (orig_mtime, orig_mtime))
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("01 Track.mp3", str(test_file), "MP3", False, True, 10),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        convert_album(album, dest_dir)
        jb7_file = dest_dir / "Artist   Album" / "01 Track.mp3"
        assert jb7_file.exists()
        import stat
        assert abs(jb7_file.stat().st_mtime - orig_mtime) < 2
