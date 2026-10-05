"""
Unit tests for Context Compactor and 3-Stage Token Optimization.
"""

from steward.core.context_compactor import ContextCompactor


def test_compactor_tool_output_truncation():
    compactor = ContextCompactor(max_tool_chars=100)
    huge_output = "A" * 500
    truncated = compactor.truncate_tool_output(huge_output)
    assert len(truncated) < 300
    assert "Truncated" in truncated


def test_compactor_distill_reasoning():
    compactor = ContextCompactor()
    messages = [
        {"role": "user", "content": "Help me build this"},
        {
            "role": "assistant",
            "content": "<think>Very long internal model reasoning</think>Here is the solution",
        },
    ]
    distilled = compactor.distill_messages_for_llm(messages)
    assert "<think>" not in distilled[1]["content"]
    assert "Here is the solution" in distilled[1]["content"]


def test_compactor_sliding_window_compaction():
    # Set low threshold to trigger compaction
    compactor = ContextCompactor(compact_threshold=50)

    messages = [
        {"role": "system", "content": "System directive"},
        {"role": "user", "content": "Query 1 " * 20},
        {"role": "assistant", "content": "Answer 1 " * 20},
        {"role": "user", "content": "Query 2 " * 20},
        {"role": "assistant", "content": "Answer 2 " * 20},
        {"role": "user", "content": "Latest query"},
    ]

    compacted = compactor.compact_history(messages, preserve_recent_turns=2)
    assert len(compacted) < len(messages)
    # Check that system checkpoint summary was inserted
    has_summary = any("Summary of Prior Execution" in str(m.get("content")) for m in compacted)
    assert has_summary is True
    # Latest message preserved
    assert compacted[-1]["content"] == "Latest query"
