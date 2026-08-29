from aitest.providers.echo import EchoProvider
from aitest.providers.openai import OpenAIProvider


def test_echo_provider():
    p = EchoProvider()
    s = p.complete("hi")
    assert "hi" in s
    assert p.embed(["a", "bb"]) == [[1.0], [2.0]]


def test_openai_no_key_raises():
    import pytest
    p = OpenAIProvider(api_key="")
    with pytest.raises(RuntimeError):
        p.complete("hi")
