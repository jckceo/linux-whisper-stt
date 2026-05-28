from __future__ import annotations

from dataclasses import dataclass

from .clipboard import copy_to_clipboard
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
    ):
        self.config = config
        self.copy_fn = copy_fn
        self.paste_fn = paste_fn
        self.available_fn = available_fn

    def deliver(self, text: str) -> DeliveryResult:
        self.copy_fn(text)
        if self.config.general.paste_mode == "auto" and self.available_fn():
            try:
                self.paste_fn()
                return DeliveryResult(True, "Pasted")
            except Exception as e:
                return DeliveryResult(
                    False, f"Copied to clipboard (paste failed: {e}). Press Ctrl+V"
                )
        return DeliveryResult(False, "Ready in clipboard — press Ctrl+V")
