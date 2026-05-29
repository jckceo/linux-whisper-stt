# Security

## Desktop Input Permissions

Auto-paste is optional. When installed with `--with-autopaste`,
linux-whisper-stt uses ydotool, which requires access to `/dev/uinput`.
That access allows desktop input injection, so it should be treated as a
privileged desktop permission.

To avoid input injection, leave auto-paste disabled and use clipboard-only
output:

```toml
[general]
paste_mode = "clipboard_only"
```

## Local Whisper Setup

The `--with-local-whisper` installer option downloads and builds third-party
code from `whisper.cpp`. Use it only when you want local transcription and are
comfortable building that dependency on your machine.

## OpenAI API Key Storage

OpenAI API keys are stored in the system keyring, not in the TOML config file.
The keyring entry uses:

```text
service: linux-whisper-stt
username: openai
```

## Reporting Security Issues

Report security issues through GitHub private vulnerability reporting or a
GitHub Security Advisory for this repository when that option is available. If
private reporting is unavailable, open a minimal public issue asking for a
private security contact and do not disclose exploit details.

Do not include API keys, recorded audio, dictation history, transcripts, or
other private content in reports. Describe the impact, affected version,
reproduction steps, and any relevant system details without attaching sensitive
data.
