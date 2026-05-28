import pytest
from pathlib import Path

from src.scanner import (
    get_file_type, check_drm, has_track_number,
    scan_directory, TrackInfo, AlbumInfo, ScanResult,
    SUPPORTED_EXTENSIONS,
)


class TestGetFileType:
    def test_mp3(self):
        assert get_file_type("test.mp3") == "MP3"

    def test_m4p(self):
        assert get_file_type("test.m4p") == "AAC (protected)"

    def test_m4a_aac(self, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                self.info = type("MockInfo", (), {
                    "codec": "AAC",
                    "codec_description": "AAC",
                })()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert get_file_type("test.m4a") == "AAC"

    def test_m4a_alac(self, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                self.info = type("MockInfo", (), {
                    "codec": "ALAC",
                    "codec_description": "Apple Lossless",
                })()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert get_file_type("test.m4a") == "ALAC"

    def test_m4a_alac_from_description(self, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                self.info = type("MockInfo", (), {
                    "codec": "AAC",
                    "codec_description": "Apple ALAC",
                })()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert get_file_type("test.m4a") == "ALAC"

    def test_m4a_codec_description_only(self, monkeypatch):
        class MockInfo:
            def __init__(self):
                self.codec_description = "AAC"
        class MockMP4:
            def __init__(self, path):
                self.info = MockInfo()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert get_file_type("test.m4a") == "AAC"

    def test_m4a_exception_returns_aac(self, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                raise ValueError("corrupt file")
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert get_file_type("test.m4a") == "AAC"

    def test_mp4(self, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                self.info = type("MockInfo", (), {
                    "codec": "AAC",
                    "codec_description": "AAC",
                })()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert get_file_type("test.mp4") == "AAC"

    def test_flac(self):
        assert get_file_type("test.flac") == "FLAC"

    def test_aiff(self):
        assert get_file_type("test.aiff") == "AIFF"

    def test_aif(self):
        assert get_file_type("test.aif") == "AIFF"

    def test_wav(self):
        assert get_file_type("test.wav") == "WAV"

    def test_wma(self):
        assert get_file_type("test.wma") == "WMA"

    def test_ogg(self):
        assert get_file_type("test.ogg") == "OGG"

    def test_unknown(self):
        assert get_file_type("test.txt") == "Unknown"

    def test_no_extension(self):
        assert get_file_type("test") == "Unknown"

    def test_uppercase_extension(self):
        assert get_file_type("test.MP3") == "MP3"

    def test_flac_uppercase(self):
        assert get_file_type("test.FLAC") == "FLAC"


class TestCheckDRM:
    def test_m4p(self):
        assert check_drm("test.m4p") is True

    def test_m4a_free(self, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                self.info = type("MockInfo", (), {})()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert check_drm("test.m4a") is False

    def test_m4a_protected(self, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                raise Exception("FairPlay DRM")
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert check_drm("test.m4a") is True

    def test_mp3(self):
        assert check_drm("test.mp3") is False

    def test_flac(self):
        assert check_drm("test.flac") is False

    def test_wav(self):
        assert check_drm("test.wav") is False

    def test_aiff(self):
        assert check_drm("test.aiff") is False

    def test_m4a_tags_none(self, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                self.info = type("MockInfo", (), {})()
                self.tags = None
        monkeypatch.setattr("src.scanner.MP4", MockMP4)
        assert check_drm("test.m4a") is False

    def test_unknown_extension(self):
        assert check_drm("test.txt") is False


class TestHasTrackNumber:
    def test_space_separator(self):
        assert has_track_number("01 Track.mp3") is True

    def test_dot_separator(self):
        assert has_track_number("01.Track.mp3") is True

    def test_dash_separator(self):
        assert has_track_number("01-Track.mp3") is True

    def test_underscore_separator(self):
        assert has_track_number("01_Track.mp3") is True

    def test_paren_separator(self):
        assert has_track_number("01)Track.mp3") is True

    def test_two_digit(self):
        assert has_track_number("12 Track.mp3") is True

    def test_three_digit(self):
        assert has_track_number("101 Track.mp3") is True

    def test_no_digit(self):
        assert has_track_number("Track.mp3") is False

    def test_no_separator(self):
        assert has_track_number("01Track.mp3") is False

    def test_letter_prefix(self):
        assert has_track_number("A01 Track.mp3") is False

    def test_just_number(self):
        assert has_track_number("01.mp3") is False

    def test_empty_stem(self):
        assert has_track_number(".mp3") is False

    def test_only_digits_stem(self):
        assert has_track_number("12345.m4a") is False

    def test_empty_string(self):
        assert has_track_number("") is False

    def test_m4a_with_number(self):
        assert has_track_number("01 Song.m4a") is True

    def test_flac_with_number(self):
        assert has_track_number("01 Song.flac") is True

    def test_wav_with_number(self):
        assert has_track_number("01 Song.wav") is True

    def test_leading_zero(self):
        assert has_track_number("001 Track.mp3") is True

    def test_disc_prefix(self):
        assert has_track_number("1-01 Track.mp3") is True

    def test_disc_prefix_two_digit(self):
        assert has_track_number("12-01 Track.mp3") is True


class TestAlbumInfo:
    def test_track_count_ok(self):
        tracks = [
            TrackInfo(f"0{i} T.mp3", f"/p/{i}", "MP3", False, True, 100)
            for i in range(1, 5)
        ]
        album = AlbumInfo("A", "Art", tracks, min_tracks=4)
        assert album.track_count_ok is True

    def test_track_count_not_ok(self):
        tracks = [
            TrackInfo(f"0{i} T.mp3", f"/p/{i}", "MP3", False, True, 100)
            for i in range(1, 3)
        ]
        album = AlbumInfo("A", "Art", tracks, min_tracks=4)
        assert album.track_count_ok is False

    def test_track_count_empty(self):
        album = AlbumInfo("A", "Art", [], min_tracks=4)
        assert album.track_count_ok is False

    def test_track_count_exact(self):
        tracks = [
            TrackInfo(f"0{i} T.mp3", f"/p/{i}", "MP3", False, True, 100)
            for i in range(1, 5)
        ]
        album = AlbumInfo("A", "Art", tracks, min_tracks=4)
        assert album.track_count_ok is True

    def test_has_track_numbers_all(self):
        tracks = [
            TrackInfo("01 T.mp3", "/p/1", "MP3", False, True, 100),
            TrackInfo("02 T.mp3", "/p/2", "MP3", False, True, 100),
        ]
        album = AlbumInfo("A", "Art", tracks)
        assert album.has_track_numbers is True

    def test_has_track_numbers_some_missing(self):
        tracks = [
            TrackInfo("01 T.mp3", "/p/1", "MP3", False, True, 100),
            TrackInfo("Song.mp3", "/p/2", "MP3", False, False, 100),
        ]
        album = AlbumInfo("A", "Art", tracks)
        assert album.has_track_numbers is False

    def test_has_track_numbers_empty(self):
        album = AlbumInfo("A", "Art", [])
        assert album.has_track_numbers is False

    def test_has_drm_true(self):
        tracks = [
            TrackInfo("01 T.mp3", "/p/1", "MP3", False, True, 100),
            TrackInfo("02 T.m4p", "/p/2", "AAC (protected)", True, True, 100),
        ]
        album = AlbumInfo("A", "Art", tracks)
        assert album.has_drm is True

    def test_has_drm_false(self):
        tracks = [
            TrackInfo("01 T.mp3", "/p/1", "MP3", False, True, 100),
        ]
        album = AlbumInfo("A", "Art", tracks)
        assert album.has_drm is False

    def test_has_drm_empty(self):
        album = AlbumInfo("A", "Art", [])
        assert album.has_drm is False

    def test_has_drm_all_protected(self):
        tracks = [
            TrackInfo("01 T.m4p", "/p/1", "AAC (protected)", True, True, 100),
            TrackInfo("02 T.m4p", "/p/2", "AAC (protected)", True, True, 100),
        ]
        album = AlbumInfo("A", "Art", tracks)
        assert album.has_drm is True


class TestScanDirectory:
    def test_nonexistent(self):
        result = scan_directory("/nonexistent/path_xyz")
        assert result.total_files == 0
        assert result.artists == {}

    def test_empty_directory(self, tmp_path):
        result = scan_directory(str(tmp_path))
        assert result.total_files == 0
        assert result.artists == {}

    def test_no_audio_files(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "cover.jpg").write_bytes(b"image")
        (d / "info.txt").write_bytes(b"text")
        result = scan_directory(str(tmp_path))
        assert result.total_files == 0

    def test_basic_mp3(self, tmp_path):
        d = tmp_path / "Test Artist" / "Test Album"
        d.mkdir(parents=True)
        (d / "01 Track.mp3").write_bytes(b"audio")
        (d / "02 Track.mp3").write_bytes(b"audio")
        result = scan_directory(str(tmp_path), min_tracks=1)
        assert result.total_files == 2
        assert "Test Artist" in result.artists
        assert "Test Album" in result.artists["Test Artist"]
        album = result.artists["Test Artist"]["Test Album"]
        assert len(album.tracks) == 2
        assert album.has_track_numbers is True
        assert album.track_count_ok is True
        assert album.has_drm is False
        assert result.file_types.get("MP3", 0) == 2
        assert result.drm_free.get("MP3", 0) == 2

    def test_multiple_artists_albums(self, tmp_path, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                self.info = type("MockInfo", (), {
                    "codec": "AAC",
                    "codec_description": "AAC",
                })()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)

        (tmp_path / "Artist A" / "Album 1").mkdir(parents=True)
        (tmp_path / "Artist A" / "Album 1" / "01 Song.mp3").write_bytes(b"d")
        (tmp_path / "Artist A" / "Album 2").mkdir(parents=True)
        (tmp_path / "Artist A" / "Album 2" / "01 Song.m4a").write_bytes(b"d")
        (tmp_path / "Artist B" / "Album 1").mkdir(parents=True)
        (tmp_path / "Artist B" / "Album 1" / "01 Song.mp3").write_bytes(b"d")

        result = scan_directory(str(tmp_path))
        assert result.total_files == 3
        assert len(result.artists) == 2
        assert len(result.artists["Artist A"]) == 2
        assert len(result.artists["Artist B"]) == 1

    def test_small_album_detected(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 T.mp3").write_bytes(b"d")
        (d / "02 T.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path), min_tracks=4)
        assert len(result.small_albums) == 1
        assert result.small_albums[0].name == "Album"

    def test_small_album_not_flagged(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        for i in range(1, 6):
            (d / f"0{i} T.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path), min_tracks=4)
        assert len(result.small_albums) == 0

    def test_untracked_detected(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "Song A.mp3").write_bytes(b"d")
        (d / "Song B.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path))
        assert len(result.untracked_albums) == 1

    def test_untracked_mixed(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 Track.mp3").write_bytes(b"d")
        (d / "Song.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path))
        assert len(result.untracked_albums) == 1

    def test_protected_album_detected(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 Track.m4p").write_bytes(b"d")
        (d / "02 Track.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path))
        assert len(result.protected_albums) == 1

    def test_protected_album_all_protected(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 Track.m4p").write_bytes(b"d")
        (d / "02 Track.m4p").write_bytes(b"d")
        result = scan_directory(str(tmp_path))
        assert len(result.protected_albums) == 1
        drm_total = sum(
            sum(1 for t in a.tracks if t.drm_protected)
            for a in result.protected_albums
        )
        assert drm_total == 2

    def test_hidden_dirs_skipped(self, tmp_path):
        (tmp_path / ".hidden" / "Album").mkdir(parents=True)
        (tmp_path / ".hidden" / "Album" / "01 T.mp3").write_bytes(b"d")
        (tmp_path / "Visible" / "Album").mkdir(parents=True)
        (tmp_path / "Visible" / "Album" / "01 T.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path))
        assert ".hidden" not in result.artists
        assert "Visible" in result.artists

    def test_hidden_album_dir_skipped(self, tmp_path):
        (tmp_path / "Artist" / ".hidden_album").mkdir(parents=True)
        (tmp_path / "Artist" / ".hidden_album" / "01 T.mp3").write_bytes(b"d")
        (tmp_path / "Artist" / "Visible").mkdir(parents=True)
        (tmp_path / "Artist" / "Visible" / "01 T.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path))
        assert "Artist" in result.artists
        assert ".hidden_album" not in result.artists["Artist"]
        assert "Visible" in result.artists["Artist"]

    def test_subdir_in_album_skipped(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "subdir").mkdir()
        (d / "01 Track.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path))
        assert result.total_files == 1
        assert len(result.artists["Artist"]["Album"].tracks) == 1

    def test_oserror_on_stat(self, tmp_path, monkeypatch):
        import pathlib
        original_stat = pathlib.Path.stat

        def mock_stat(self):
            if "error_file" in str(self):
                raise OSError("permission denied")
            return original_stat(self)

        monkeypatch.setattr(pathlib.Path, "stat", mock_stat)

        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 OK.mp3").write_bytes(b"ok")
        (d / "02 error_file.mp3").write_bytes(b"error")

        result = scan_directory(str(tmp_path))
        assert result.total_files == 2
        album = result.artists["Artist"]["Album"]
        assert len(album.tracks) == 2
        for t in album.tracks:
            if t.filename == "02 error_file.mp3":
                assert t.size_bytes == 0
            else:
                assert t.size_bytes > 0

    def test_m4a_alac_in_scan(self, tmp_path, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                self.info = type("MockInfo", (), {
                    "codec": "ALAC",
                    "codec_description": "Apple Lossless",
                })()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)

        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 Track.m4a").write_bytes(b"d")

        result = scan_directory(str(tmp_path))
        assert result.file_types.get("ALAC", 0) == 1
        assert result.drm_free.get("ALAC", 0) == 1

    def test_m4a_drm_protected_in_scan(self, tmp_path, monkeypatch):
        class MockProtectedMP4:
            def __init__(self, path):
                raise Exception("DRM protected")
        monkeypatch.setattr("src.scanner.MP4", MockProtectedMP4)

        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 Track.m4a").write_bytes(b"d")

        result = scan_directory(str(tmp_path))
        assert result.file_types.get("AAC", 0) == 1
        assert result.drm_protected.get("AAC", 0) == 1

    def test_multiple_file_types(self, tmp_path, monkeypatch):
        class MockMP4:
            def __init__(self, path):
                codec_name = "ALAC" if "alac" in str(path).lower() else "AAC"
                self.info = type("MockInfo", (), {
                    "codec": codec_name,
                    "codec_description": codec_name,
                })()
                self.tags = {}
        monkeypatch.setattr("src.scanner.MP4", MockMP4)

        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 T.mp3").write_bytes(b"d")
        (d / "02 T.m4a").write_bytes(b"d")
        (d / "03 T.m4a").write_bytes(b"d")
        (d / "04 T.flac").write_bytes(b"d")

        result = scan_directory(str(tmp_path))
        assert result.file_types.get("MP3", 0) == 1
        assert result.file_types.get("AAC", 0) == 2
        assert result.file_types.get("FLAC", 0) == 1

    def test_various_audio_formats(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 T.mp3").write_bytes(b"d")
        (d / "02 T.flac").write_bytes(b"d")
        (d / "03 T.aiff").write_bytes(b"d")
        (d / "04 T.aif").write_bytes(b"d")
        (d / "05 T.wav").write_bytes(b"d")
        (d / "06 T.wma").write_bytes(b"d")
        (d / "07 T.ogg").write_bytes(b"d")

        result = scan_directory(str(tmp_path))
        assert result.file_types.get("MP3", 0) == 1
        assert result.file_types.get("FLAC", 0) == 1
        assert result.file_types.get("AIFF", 0) == 2
        assert result.file_types.get("WAV", 0) == 1
        assert result.file_types.get("WMA", 0) == 1
        assert result.file_types.get("OGG", 0) == 1
        assert result.total_files == 7

    def test_scan_result_counts(self, tmp_path):
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 T.mp3").write_bytes(b"d")
        (d / "02 T.mp3").write_bytes(b"d")
        (d / "03 T.m4p").write_bytes(b"d")

        result = scan_directory(str(tmp_path))
        assert result.total_files == 3
        assert result.file_types.get("MP3", 0) == 2
        assert result.file_types.get("AAC (protected)", 0) == 1
        assert result.drm_free.get("MP3", 0) == 2
        assert result.drm_protected.get("AAC (protected)", 0) == 1

    def test_empty_artist_dir(self, tmp_path):
        (tmp_path / "Empty Artist").mkdir()
        result = scan_directory(str(tmp_path))
        assert result.total_files == 0
        assert "Empty Artist" in result.artists
        assert result.artists["Empty Artist"] == {}

    def test_non_dir_in_source_skipped(self, tmp_path):
        (tmp_path / "file.txt").write_bytes(b"not a dir")
        d = tmp_path / "Artist" / "Album"
        d.mkdir(parents=True)
        (d / "01 T.mp3").write_bytes(b"d")
        result = scan_directory(str(tmp_path))
        assert result.total_files == 1




class TestScanResult:
    def test_empty_construction(self):
        result = ScanResult(
            artists={},
            total_files=0,
            file_types={},
            drm_free={},
            drm_protected={},
            small_albums=[],
            untracked_albums=[],
            protected_albums=[],
        )
        assert result.total_files == 0
        assert result.artists == {}

    def test_with_data(self):
        track = TrackInfo("01 T.mp3", "/p", "MP3", False, True, 100)
        album = AlbumInfo("A", "Art", [track])
        result = ScanResult(
            artists={"Art": {"A": album}},
            total_files=1,
            file_types={"MP3": 1},
            drm_free={"MP3": 1},
            drm_protected={},
            small_albums=[album],
            untracked_albums=[],
            protected_albums=[],
        )
        assert result.total_files == 1
        assert result.small_albums[0].name == "A"


class TestTrackInfo:
    def test_construction(self):
        t = TrackInfo("01 T.mp3", "/p", "MP3", False, True, 100)
        assert t.filename == "01 T.mp3"
        assert t.file_type == "MP3"
        assert t.drm_protected is False
        assert t.has_track_number is True
        assert t.size_bytes == 100

    def test_drm_protected(self):
        t = TrackInfo("track.m4p", "/p", "AAC (protected)", True, False, 200)
        assert t.drm_protected is True
        assert t.has_track_number is False


class TestSupportedExtensions:
    def test_common_formats_present(self):
        assert ".mp3" in SUPPORTED_EXTENSIONS
        assert ".m4a" in SUPPORTED_EXTENSIONS
        assert ".m4p" in SUPPORTED_EXTENSIONS
        assert ".mp4" in SUPPORTED_EXTENSIONS
        assert ".flac" in SUPPORTED_EXTENSIONS
        assert ".wav" in SUPPORTED_EXTENSIONS
