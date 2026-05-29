import stat

from linux_whisper_stt.open_with import (
    desktop_entry_text,
    install_open_with,
    mime_types,
)


def test_mime_types_include_common_audio_and_video_formats():
    types = mime_types()

    assert "audio/mpeg" in types
    assert "audio/wav" in types
    assert "audio/x-wav" in types
    assert "audio/flac" in types
    assert "audio/ogg" in types
    assert "audio/mp4" in types
    assert "video/mp4" in types
    assert "video/x-matroska" in types
    assert "video/x-msvideo" in types
    assert "video/quicktime" in types


def test_desktop_entry_text_registers_transcribe_file_action():
    entry = desktop_entry_text("/opt/linux-whisper-stt/bin/linux-whisper-stt")

    assert "Name=Transcribe with linux-whisper-stt\n" in entry
    assert "Exec=/opt/linux-whisper-stt/bin/linux-whisper-stt transcribe-file %f\n" in entry
    assert "NoDisplay=true\n" in entry
    assert "Terminal=false\n" in entry
    assert "Categories=AudioVideo;Audio;Video;\n" in entry

    mime_line = next(line for line in entry.splitlines() if line.startswith("MimeType="))
    assert mime_line.endswith(";")
    for mime_type in mime_types():
        assert f"{mime_type};" in mime_line


def test_install_open_with_writes_desktop_file(tmp_path):
    path = install_open_with("linux-whisper-stt", applications_dir=tmp_path)

    assert path == tmp_path / "linux-whisper-stt-transcribe.desktop"
    assert path.read_text() == desktop_entry_text("linux-whisper-stt")
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
