from __future__ import annotations

from openbase_coder_cli.livekit_agent.speech_formatter import (
    SpeechFormatOptions,
    format_for_speech,
    format_for_speech_segments,
)


def test_formatter_preserves_list_structure_before_cleanup():
    text = """Fixed:
1. Preserved newlines before parsing.
2. Added API and TTS replacements.
3. Skipped code blocks."""

    assert (
        format_for_speech(text)
        == "Fixed. One: Preserved newlines before parsing. Two: Added A P I and T T S replacements. Three: Skipped code blocks."
    )


def test_formatter_suppresses_code_blocks_and_humanizes_identifiers():
    text = """## Next steps

- Update README.md
- Run `uv run pytest`
- Keep `formatForSpeech()` private for now

```ts
console.log("do not speak this");
```"""

    assert format_for_speech_segments(text) == [
        "Section: Next steps.",
        "Item: Update read me dot M D.",
        "Item: Run U V run pytest.",
        "Item: Keep format for speech private for now.",
        "Omitted.",
    ]
    assert "console.log" not in format_for_speech(text)


def test_formatter_reduces_omitted_code_narration_to_one_word():
    text = """I checked the output.

Code block omitted, shown on screen. It is Python, one line.

bash code omitted

bash one line

Done."""

    assert format_for_speech(text) == "I checked the output. Omitted. Done."


def test_formatter_splits_paths_filenames_and_identifier_styles():
    text = (
        "Changed src/utils/parseMarkdown.ts, OPENAI_API_KEY, "
        "snake_case, kebab-case, JSON, CLI, and STT."
    )

    assert (
        format_for_speech(text)
        == "Changed parse markdown dot T S in src slash utils, openai A P I key, snake case, kebab case, J S O N, C L I, and S T T."
    )


def test_formatter_pronounces_saas_and_sas_as_words():
    text = "SaaS billing, SAS analytics, SAAS metrics, and SaaSConfig.ts changed."

    assert (
        format_for_speech(text)
        == "sass billing, sass analytics, sass metrics, and sass config dot T S changed."
    )


def test_formatter_keeps_existing_acronyms_spelled_as_letters():
    text = "API, CLI, TTS, STT, and LLM remain explicit acronyms."

    assert (
        format_for_speech(text)
        == "A P I, C L I, T T S, S T T, and L L M remain explicit acronyms."
    )


def test_formatter_omits_stack_traces_and_log_like_output():
    text = """Traceback (most recent call last):
  File "app.py", line 2, in <module>
Exception: nope"""

    assert format_for_speech(text) == "Technical output omitted, shown on screen."


def test_formatter_truncates_after_speech_formatting():
    text = "- First API item.\n- Second TTS item.\n- Third STT item."

    assert (
        format_for_speech(text, SpeechFormatOptions(max_chars=48))
        == "Item: First A P I item. Item: Second T T S item."
    )
