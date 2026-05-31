import os
from pathlib import Path

from src.converter import (
    make_jb7_dirname, convert_album, convert_selected, _parse_disc_prefix,
)
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

    def test_with_disc_num(self):
        assert make_jb7_dirname("Artist", "Album", 1) == "Artist   Album CD1"
        assert make_jb7_dirname("Artist", "Album", 12) == "Artist   Album CD12"

    def test_underscore_in_artist(self):
        assert make_jb7_dirname("Some_Artist", "Album") == "Some-Artist   Album"

    def test_underscore_in_album(self):
        assert make_jb7_dirname("Artist", "Greatest_Hits") == "Artist   Greatest-Hits"

    def test_underscore_with_disc(self):
        assert make_jb7_dirname("Some_Artist", "Greatest_Hits", 2) == "Some-Artist   Greatest-Hits CD2"


    def test_with_suffix(self):
        assert make_jb7_dirname("Artist", "Album", suffix="[DL]") == "Artist   Album [DL]"

    def test_with_suffix_and_disc(self):
        assert make_jb7_dirname("Artist", "Album", disc_num=1, suffix="[DL]") == "Artist   Album CD1 [DL]"

    def test_empty_suffix(self):
        assert make_jb7_dirname("Artist", "Album", suffix="") == "Artist   Album"


class TestParseDiscPrefix:
    def test_single_disc(self):
        disc, clean = _parse_disc_prefix("1-01 Song.mp3")
        assert disc == 1
        assert clean == "01 Song.mp3"

    def test_double_disc(self):
        disc, clean = _parse_disc_prefix("12-03 Song.mp3")
        assert disc == 12
        assert clean == "03 Song.mp3"

    def test_no_prefix(self):
        disc, clean = _parse_disc_prefix("01 Song.mp3")
        assert disc is None
        assert clean == "01 Song.mp3"

    def test_no_prefix_plain(self):
        disc, clean = _parse_disc_prefix("Song.mp3")
        assert disc is None
        assert clean == "Song.mp3"

    def test_disc_with_two_digit_track(self):
        disc, clean = _parse_disc_prefix("2-123 Song.mp3")
        assert disc == 2
        assert clean == "123 Song.mp3"

    def test_underscore_not_mistaken_for_dash(self):
        disc, clean = _parse_disc_prefix("1_01 Song.mp3")
        assert disc is None
        assert clean == "1_01 Song.mp3"


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

    def test_copy2_fallback_to_copy(self, tmp_path, monkeypatch):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        test_file = src_dir / "01 Track.mp3"
        test_file.write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        def mock_copy2(*args, **kwargs):
            raise IOError("Operation not permitted")

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
        assert count == 1
        assert (dest_dir / "Artist   Album" / "01 Track.mp3").exists()

    def test_copy2_fallback_with_callback(self, tmp_path, monkeypatch):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        test_file = src_dir / "01 Track.mp3"
        test_file.write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        def mock_copy2(*args, **kwargs):
            raise IOError("Operation not permitted")

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
        assert count == 1
        assert any("no metadata" in m for m in messages)

    def test_both_copy_fail(self, tmp_path, monkeypatch):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        test_file = src_dir / "01 Track.mp3"
        test_file.write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        def mock_copy2(*args, **kwargs):
            raise IOError("Disk full")

        def mock_copy(*args, **kwargs):
            raise IOError("Disk full")

        monkeypatch.setattr("shutil.copy2", mock_copy2)
        monkeypatch.setattr("shutil.copy", mock_copy)

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

    def test_both_copy_fail_with_callback(self, tmp_path, monkeypatch):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        test_file = src_dir / "01 Track.mp3"
        test_file.write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        def mock_copy2(*args, **kwargs):
            raise IOError("Disk full")

        def mock_copy(*args, **kwargs):
            raise IOError("Disk full")

        monkeypatch.setattr("shutil.copy2", mock_copy2)
        monkeypatch.setattr("shutil.copy", mock_copy)

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

    def test_multi_disc_album(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Greatest Hits"
        src_dir.mkdir(parents=True)
        (src_dir / "1-01 Song A.mp3").write_bytes(b"disc1_1")
        (src_dir / "1-02 Song B.mp3").write_bytes(b"disc1_2")
        (src_dir / "2-01 Song C.mp3").write_bytes(b"disc2_1")
        (src_dir / "2-02 Song D.mp3").write_bytes(b"disc2_2")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("1-01 Song A.mp3", str(src_dir / "1-01 Song A.mp3"), "MP3", False, True, 8),
            TrackInfo("1-02 Song B.mp3", str(src_dir / "1-02 Song B.mp3"), "MP3", False, True, 8),
            TrackInfo("2-01 Song C.mp3", str(src_dir / "2-01 Song C.mp3"), "MP3", False, True, 8),
            TrackInfo("2-02 Song D.mp3", str(src_dir / "2-02 Song D.mp3"), "MP3", False, True, 8),
        ]
        album = AlbumInfo("Greatest Hits", "Artist", tracks)

        count = convert_album(album, dest_dir)
        assert count == 4

        cd1 = dest_dir / "Artist   Greatest Hits CD1"
        cd2 = dest_dir / "Artist   Greatest Hits CD2"
        assert (cd1 / "01 Song A.mp3").exists()
        assert (cd1 / "02 Song B.mp3").exists()
        assert (cd2 / "01 Song C.mp3").exists()
        assert (cd2 / "02 Song D.mp3").exists()
        assert (cd1 / "01 Song A.mp3").read_bytes() == b"disc1_1"
        assert (cd2 / "01 Song C.mp3").read_bytes() == b"disc2_1"

    def test_multi_disc_callback(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Hits"
        src_dir.mkdir(parents=True)
        (src_dir / "1-01 A.mp3").write_bytes(b"a")
        (src_dir / "2-01 B.mp3").write_bytes(b"b")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("1-01 A.mp3", str(src_dir / "1-01 A.mp3"), "MP3", False, True, 1),
            TrackInfo("2-01 B.mp3", str(src_dir / "2-01 B.mp3"), "MP3", False, True, 1),
        ]
        album = AlbumInfo("Hits", "Artist", tracks)
        messages = []

        def cb(msg):
            messages.append(msg)

        count = convert_album(album, dest_dir, cb)
        assert count == 2
        assert any("Copied: 01 A.mp3" in m for m in messages)
        assert any("Copied: 01 B.mp3" in m for m in messages)

    def test_underscore_in_filename(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        (src_dir / "01_Track.mp3").write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("01_Track.mp3", str(src_dir / "01_Track.mp3"), "MP3", False, True, 4),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        count = convert_album(album, dest_dir)
        assert count == 1

        jb7_dir = dest_dir / "Artist   Album"
        assert (jb7_dir / "01-Track.mp3").exists()
        assert not (jb7_dir / "01_Track.mp3").exists()

    def test_underscore_in_artist_and_album(self, tmp_path):
        src_dir = tmp_path / "src" / "Some_Artist" / "Greatest_Hits"
        src_dir.mkdir(parents=True)
        (src_dir / "01 Song.mp3").write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("01 Song.mp3", str(src_dir / "01 Song.mp3"), "MP3", False, True, 4),
        ]
        album = AlbumInfo("Greatest_Hits", "Some_Artist", tracks)

        count = convert_album(album, dest_dir)
        assert count == 1

        jb7_dir = dest_dir / "Some-Artist   Greatest-Hits"
        assert jb7_dir.exists()
        assert (jb7_dir / "01 Song.mp3").exists()

    def test_mixed_disc_and_plain_tracks(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        (src_dir / "1-01 Disc Track.mp3").write_bytes(b"disc")
        (src_dir / "02 Plain Track.mp3").write_bytes(b"plain")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("1-01 Disc Track.mp3", str(src_dir / "1-01 Disc Track.mp3"), "MP3", False, True, 4),
            TrackInfo("02 Plain Track.mp3", str(src_dir / "02 Plain Track.mp3"), "MP3", False, True, 5),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        count = convert_album(album, dest_dir)
        assert count == 2

        cd1 = dest_dir / "Artist   Album CD1"
        plain = dest_dir / "Artist   Album"
        assert (cd1 / "01 Disc Track.mp3").exists()
        assert (plain / "02 Plain Track.mp3").exists()

    def test_suffix_applied(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        (src_dir / "01 Track.mp3").write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("01 Track.mp3", str(src_dir / "01 Track.mp3"), "MP3", False, True, 4),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        count = convert_album(album, dest_dir, suffix="[DL]")
        assert count == 1

        assert (dest_dir / "Artist   Album [DL]" / "01 Track.mp3").exists()

    def test_suffix_with_disc(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        (src_dir / "1-01 Track.mp3").write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("1-01 Track.mp3", str(src_dir / "1-01 Track.mp3"), "MP3", False, True, 4),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        count = convert_album(album, dest_dir, suffix="[DL]")
        assert count == 1

        assert (dest_dir / "Artist   Album CD1 [DL]" / "01 Track.mp3").exists()

    def test_suffix_with_callback(self, tmp_path):
        src_dir = tmp_path / "src" / "Artist" / "Album"
        src_dir.mkdir(parents=True)
        (src_dir / "01 Track.mp3").write_bytes(b"data")
        dest_dir = tmp_path / "dest"

        tracks = [
            TrackInfo("01 Track.mp3", str(src_dir / "01 Track.mp3"), "MP3", False, True, 4),
        ]
        album = AlbumInfo("Album", "Artist", tracks)

        def cb(msg):
            pass

        count = convert_album(album, dest_dir, cb, suffix="[X]")
        assert count == 1
        assert (dest_dir / "Artist   Album [X]" / "01 Track.mp3").exists()


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

    def test_selected_with_suffix(self, tmp_path):
        d = tmp_path / "src" / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 T.mp3").write_bytes(b"d")
        album = AlbumInfo("Album", "Artist", [
            TrackInfo("01 T.mp3", str(d / "01 T.mp3"), "MP3", False, True, 1),
        ])
        selected = {"Artist": {"Album": album}}
        dest_dir = tmp_path / "dest"

        total = convert_selected(selected, str(dest_dir), suffix="[DL]")
        assert total == 1
        assert (dest_dir / "Artist   Album [DL]" / "01 T.mp3").exists()

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
