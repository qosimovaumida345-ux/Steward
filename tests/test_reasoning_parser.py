"""
Unit tests for RobustReasoningParser streaming lookahead state machine.
"""

import pytest
from steward.brain.reasoning_parser import RobustReasoningParser, StreamingParserState


def test_parser_basic_think_block():
    parser = RobustReasoningParser()
    text = "Intro<think>internal logic</think>Final Answer"
    r, c = parser.feed(text)
    fr, fc = parser.flush()
    assert (r + fr) == "internal logic"
    assert (c + fc) == "IntroFinal Answer"


def test_parser_split_open_tag():
    parser = RobustReasoningParser()
    # "<think>" split across 2 chunks: "<thi" and "nk>reasoning</think>output"
    r1, c1 = parser.feed("Hello <thi")
    assert r1 == ""
    assert c1 == "Hello "

    r2, c2 = parser.feed("nk>pondering</think> done")
    assert r2 == "pondering"
    assert c2 == " done"

    fr, fc = parser.flush()
    assert fr == ""
    assert fc == ""


def test_parser_split_close_tag():
    parser = RobustReasoningParser()
    # "</think>" split across 2 chunks: "</thi" and "nk>"
    r1, c1 = parser.feed("<think>reasoning </thi")
    assert r1 == "reasoning "
    assert c1 == ""

    r2, c2 = parser.feed("nk>answer content")
    assert r2 == ""
    assert c2 == "answer content"

    fr, fc = parser.flush()
    assert fr == ""
    assert fc == ""


def test_parser_unclosed_tag_flush():
    parser = RobustReasoningParser()
    r1, c1 = parser.feed("<think>unclosed thought")
    fr, fc = parser.flush()
    assert (r1 + fr) == "unclosed thought"
    assert (c1 + fc) == ""


def test_parser_multiple_think_blocks():
    parser = RobustReasoningParser()
    stream = ["<think>step1", "</think>part1", "<think>step2", "</think>part2"]
    reasoning = []
    content = []
    for chunk in stream:
        r, c = parser.feed(chunk)
        reasoning.append(r)
        content.append(c)
    fr, fc = parser.flush()
    reasoning.append(fr)
    content.append(fc)

    assert "".join(reasoning) == "step1step2"
    assert "".join(content) == "part1part2"
