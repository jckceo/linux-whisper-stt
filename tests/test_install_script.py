from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "install.sh"


def script_text() -> str:
    return SCRIPT.read_text()


def test_install_script_documents_optional_flags():
    text = script_text()
    assert "--with-autopaste" in text
    assert "--with-local-whisper" in text
    assert "--help" in text


def test_base_install_does_not_install_autopaste_packages_before_flag_block():
    text = script_text()
    before_autopaste = text.split('if [ "$WITH_AUTOPASTE" = "1" ]')[0]
    assert "ydotool" not in before_autopaste
    assert "ydotoold" not in before_autopaste
    assert "usermod -aG input" not in before_autopaste
    assert "/etc/udev/rules.d/80-uinput.rules" not in before_autopaste


def test_local_whisper_build_is_behind_explicit_flag():
    text = script_text()
    before_local = text.split('if [ "$WITH_LOCAL_WHISPER" = "1" ]')[0]
    assert "git clone https://github.com/ggml-org/whisper.cpp" not in before_local
    assert "download-ggml-model.sh" not in before_local


def test_base_install_does_not_install_local_whisper_build_packages():
    text = script_text()
    before_local = text.split('if [ "$WITH_LOCAL_WHISPER" = "1" ]')[0]
    package_section = before_local.split('echo "==> System packages (sudo)"', 1)[1]

    assert "build-essential" not in package_section
    assert "cmake" not in package_section
    assert "git" not in package_section
