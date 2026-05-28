from pathlib import Path

from linux_whisper_stt.assets import asset_path


def test_asset_path_points_into_package():
    p = asset_path("sounds", "start.wav")
    assert isinstance(p, Path)
    assert p.parts[-2:] == ("sounds", "start.wav")
    assert "assets" in p.parts
