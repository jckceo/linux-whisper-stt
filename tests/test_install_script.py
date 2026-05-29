from pathlib import Path


def test_install_script_installs_ydotool_daemon_package():
    install_script = Path(__file__).resolve().parents[1] / "install.sh"
    lines = install_script.read_text().splitlines()
    install_start = next(
        i for i, line in enumerate(lines) if line.strip() == "sudo apt-get install -y \\"
    )
    package_lines = []
    for line in lines[install_start + 1 :]:
        stripped = line.strip()
        if not stripped:
            break
        package_lines.extend(stripped.rstrip("\\").split())

    assert "ydotool" in package_lines
    assert "ydotoold" in package_lines
