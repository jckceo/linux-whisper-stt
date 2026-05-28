from linux_whisper_stt.config import Config
from linux_whisper_stt.output.manager import DeliveryResult, OutputManager


def make_manager(paste_mode="auto", available=True, paste_raises=False):
    cfg = Config()
    cfg.general.paste_mode = paste_mode
    copied = []
    pasted = []

    def copy_fn(text):
        copied.append(text)

    def paste_fn():
        if paste_raises:
            raise RuntimeError("uinput denied")
        pasted.append(True)

    mgr = OutputManager(
        cfg,
        copy_fn=copy_fn,
        paste_fn=paste_fn,
        available_fn=lambda: available,
    )
    return mgr, copied, pasted


def test_auto_with_ydotool_copies_and_pastes():
    mgr, copied, pasted = make_manager(paste_mode="auto", available=True)
    result = mgr.deliver("hello")
    assert copied == ["hello"]
    assert pasted == [True]
    assert result.pasted is True


def test_auto_without_ydotool_falls_back_to_clipboard():
    mgr, copied, pasted = make_manager(paste_mode="auto", available=False)
    result = mgr.deliver("hello")
    assert copied == ["hello"]
    assert pasted == []
    assert result.pasted is False
    assert "Ctrl+V" in result.message


def test_clipboard_only_never_pastes():
    mgr, copied, pasted = make_manager(paste_mode="clipboard_only", available=True)
    result = mgr.deliver("hello")
    assert copied == ["hello"]
    assert pasted == []
    assert result.pasted is False


def test_paste_failure_falls_back_gracefully():
    mgr, copied, pasted = make_manager(paste_mode="auto", available=True, paste_raises=True)
    result = mgr.deliver("hello")
    assert copied == ["hello"]
    assert result.pasted is False
    assert "Ctrl+V" in result.message
