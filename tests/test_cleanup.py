import pytest

from chit.cleanup import Cleaner, light, looks_safe


@pytest.mark.parametrize(
    "raw, expected",
    [
        (
            "Um, so I wanted to, uh, let you know that the the meeting is on Wednesday.",
            "So I wanted to let you know that the meeting is on Wednesday.",
        ),
        ("And, you know, please, like, bring the slides.", "And, please, bring the slides."),
        ("uh i i think it's fine", "I think it's fine."),
        ("Hmm. Okay, let's go", "Okay, let's go."),
        ("You know, it works", "It works."),
        ("I like pizza", "I like pizza."),  # meaningful "like" stays
        ("what time is it?", "What time is it?"),
        ("um", ""),
        ("कल अ मीटिंग है मतलब, तीन बजे", "कल मीटिंग है तीन बजे।"),
        ("acha, kal meeting hai", "Kal meeting hai."),
    ],
)
def test_light(raw, expected):
    assert light(raw) == expected


def test_guard_accepts_real_cleanup():
    src = "um so can you send me the report by monday no wait tuesday"
    assert looks_safe(src, "Can you send me the report by Tuesday?")


def test_guard_rejects_answers_and_additions():
    src = "what is the capital of france"
    assert not looks_safe(src, "The capital of France is Paris.")
    assert not looks_safe(src, "Sure! What is the capital of France?")
    assert not looks_safe("send the file", "Please send the file to the whole team by end of day today.")
    assert not looks_safe("this is a long dictation about the quarterly plan and budget", "Okay.")


def test_guard_protects_numbers_unless_corrected():
    assert not looks_safe("the meeting is on wednesday at three", "The meeting is on Wednesday.")
    assert looks_safe("the meeting is on wednesday at three", "The meeting is on Wednesday at three.")
    assert looks_safe("book 2 tickets no wait 3 tickets", "Book 3 tickets.")


def test_guard_rejects_garbled_text():
    assert not looks_safe("मैं कल ऑफिस नहीं आ पाऊंगा", "मैं कल ऑफिस नहीं आ पा�ऊंगा।")


class FakeSmart:
    def __init__(self, out):
        self.out = out

    def rewrite(self, text, timeout_s):
        return self.out


def test_cleaner_falls_back_to_light_when_rejected():
    c = Cleaner(FakeSmart("Sure! Here is the answer: Paris."))
    assert c.clean("um what is the capital of france", "smart") == "What is the capital of france."


def test_cleaner_uses_light_on_timeout_and_short_text():
    assert (
        Cleaner(FakeSmart(None)).clean("um send me the report by tuesday please", "smart")
        == "Send me the report by tuesday please."
    )
    assert Cleaner(FakeSmart("SHOULD NOT BE USED")).clean("uh yes", "smart") == "Yes."


def test_modes():
    c = Cleaner(FakeSmart("Send me the report by Tuesday, please."))
    raw = "um send me the report by monday no wait tuesday please"
    assert c.clean(raw, "smart") == "Send me the report by Tuesday, please."
    assert c.clean(raw, "light") == "Send me the report by monday no wait tuesday please."
    assert c.clean(raw, "off") == raw
