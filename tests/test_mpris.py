from linux_whisper_stt.media.mpris import MprisController


def test_pauses_listed_players_and_tracks_them():
    paused = []
    m = MprisController(
        list_fn=lambda: ["org.mpris.MediaPlayer2.spotify",
                         "org.mpris.MediaPlayer2.firefox"],
        pause_fn=paused.append,
        resume_fn=lambda _name: None,
    )
    m.pause()
    assert paused == [
        "org.mpris.MediaPlayer2.spotify",
        "org.mpris.MediaPlayer2.firefox",
    ]
    assert m._paused == paused


def test_resume_only_resumes_players_we_paused():
    resumed = []
    m = MprisController(
        list_fn=lambda: ["org.mpris.MediaPlayer2.spotify"],
        pause_fn=lambda _name: None,
        resume_fn=resumed.append,
    )
    m.pause()
    m.resume()
    assert resumed == ["org.mpris.MediaPlayer2.spotify"]
    # state cleared so a second resume is a no-op
    resumed.clear()
    m.resume()
    assert resumed == []


def test_resume_without_pause_is_noop():
    resumed = []
    m = MprisController(
        list_fn=lambda: ["org.mpris.MediaPlayer2.spotify"],
        pause_fn=lambda _name: None,
        resume_fn=resumed.append,
    )
    m.resume()
    assert resumed == []


def test_pause_swallows_listing_errors():
    def boom():
        raise RuntimeError("no session bus")

    m = MprisController(list_fn=boom, pause_fn=lambda _n: None, resume_fn=lambda _n: None)
    m.pause()  # must not raise
    assert m._paused == []


def test_one_uncooperative_player_does_not_block_the_others():
    paused = []

    def pause(name):
        if "broken" in name:
            raise RuntimeError("DBus error")
        paused.append(name)

    m = MprisController(
        list_fn=lambda: ["org.mpris.MediaPlayer2.broken",
                         "org.mpris.MediaPlayer2.spotify"],
        pause_fn=pause,
        resume_fn=lambda _n: None,
    )
    m.pause()
    # broken one is skipped, the good one still paused and tracked for resume
    assert paused == ["org.mpris.MediaPlayer2.spotify"]
    assert m._paused == ["org.mpris.MediaPlayer2.spotify"]


def test_resume_swallows_errors_and_clears_state():
    def boom(_name):
        raise RuntimeError("DBus error")

    m = MprisController(
        list_fn=lambda: ["org.mpris.MediaPlayer2.spotify"],
        pause_fn=lambda _n: None,
        resume_fn=boom,
    )
    m.pause()
    m.resume()  # must not raise
    assert m._paused == []
