from video_player_cli.domain.supported_formats import SupportedFormats


def test_is_supported_normalizes_dot() -> None:
    supported = SupportedFormats()

    assert supported.is_supported(".mp4")
    assert supported.is_supported("MKV")
    assert not supported.is_supported("mov")
