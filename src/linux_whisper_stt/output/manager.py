from __future__ import annotations

from dataclasses import dataclass

from .clipboard import copy_to_clipboard, wait_for_clipboard
from .paste import paste_via_ydotool, ydotool_available


@dataclass
class DeliveryResult:
    pasted: bool
    message: str


class OutputManager:
    def __init__(
        self,
        config,
        copy_fn=copy_to_clipboard,
        paste_fn=paste_via_ydotool,
        available_fn=ydotool_available,
        wait_for_clipboard_fn=wait_for_clipboard,
    ):
        self.config = config
        self.copy_fn = copy_fn
        self.paste_fn = paste_fn
        self.available_fn = available_fn
        self.wait_for_clipboard_fn = wait_for_clipboard_fn

    def deliver(self, text: str) -> DeliveryResult:
        self.copy_fn(text)
        if self.config.general.paste_mode == "auto" and self.available_fn():
            if not self.wait_for_clipboard_fn(text):
                return DeliveryResult(
                    False,
                    "Copied to clipboard (clipboard did not update before auto-paste). "
                    "Press Ctrl+V",
                )
            try:
                self.paste_fn(text)
                return DeliveryResult(True, "Pasted")
            except Exception as e:
                return DeliveryResult(
                    False, f"Copied to clipboard (paste failed: {e}). Press Ctrl+V"
                )
        return DeliveryResult(False, "Ready in clipboard — press Ctrl+V")
