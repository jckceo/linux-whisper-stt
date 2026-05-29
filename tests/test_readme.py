from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def test_readme_mentions_codex_development():
    readme = ROOT / "README.md"
    assert "Developed with Codex 5.5 xhigh" in readme.read_text()


def test_readme_security_notes_describe_history_privacy():
    readme = (ROOT / "README.md").read_text()
    security_notes = _section(readme, "## Security Notes")

    assert "~/.local/share/linux-whisper-stt/history" in security_notes
    assert "recorded WAV" in security_notes
    assert "transcripts" in security_notes
    assert "[history]" in security_notes
    assert "enabled = false" in security_notes


def test_readme_documents_optional_installer_flags():
    readme = (ROOT / "README.md").read_text()

    assert "--with-autopaste" in readme
    assert "--with-local-whisper" in readme


def test_readme_documents_file_transcription_and_history():
    readme = (ROOT / "README.md").read_text()

    assert "Transcribe file" in readme
    assert "Open With" in readme
    assert "History" in readme
    assert "25 MB" in readme
    assert "video" in readme


def test_security_reporting_has_actionable_github_channel():
    security = (ROOT / "SECURITY.md").read_text()
    reporting = _section(security, "## Reporting Security Issues")

    assert "GitHub private vulnerability reporting" in reporting
    assert "GitHub Security Advisory" in reporting
    assert "public issue" in reporting
