"""
Streaming Reasoning Lookahead State Machine Parser.
Splits real-time SSE token stream into internal reasoning (<think>) and external content,
robustly handling split tag delimiters across chunk boundaries.
"""

from __future__ import annotations

from enum import Enum
from typing import Tuple


class StreamingParserState(Enum):
    OUTSIDE_THINK = 0
    INSIDE_THINK = 1


class RobustReasoningParser:
    """
    Lookahead buffer state machine for streaming <think> tags.
    Correctly handles tags split across network chunk boundaries (e.g., '</thi' + 'nk>').
    """

    OPEN_TAG = "<think>"
    CLOSE_TAG = "</think>"

    def __init__(self) -> None:
        self.state = StreamingParserState.OUTSIDE_THINK
        self.buffer = ""
        self.accumulated_reasoning = ""
        self.accumulated_content = ""

    def reset(self) -> None:
        self.state = StreamingParserState.OUTSIDE_THINK
        self.buffer = ""
        self.accumulated_reasoning = ""
        self.accumulated_content = ""

    def feed(self, chunk: str) -> Tuple[str, str]:
        """
        Feed an incoming string chunk into the parser.
        Returns (reasoning_delta, content_delta).
        """
        if not chunk:
            return "", ""

        self.buffer += chunk
        reasoning_out: list[str] = []
        content_out: list[str] = []

        while self.buffer:
            if self.state == StreamingParserState.OUTSIDE_THINK:
                open_pos = self.buffer.find(self.OPEN_TAG)
                if open_pos != -1:
                    # Content before tag
                    if open_pos > 0:
                        content_out.append(self.buffer[:open_pos])
                    self.buffer = self.buffer[open_pos + len(self.OPEN_TAG):]
                    self.state = StreamingParserState.INSIDE_THINK
                else:
                    # Check if the buffer ends with a partial prefix of OPEN_TAG
                    tail_len = 0
                    for i in range(len(self.OPEN_TAG) - 1, 0, -1):
                        if self.buffer.endswith(self.OPEN_TAG[:i]):
                            tail_len = i
                            break
                    if tail_len > 0:
                        prefix = self.buffer[:-tail_len]
                        if prefix:
                            content_out.append(prefix)
                        self.buffer = self.buffer[-tail_len:]
                        break
                    else:
                        content_out.append(self.buffer)
                        self.buffer = ""
            else:
                close_pos = self.buffer.find(self.CLOSE_TAG)
                if close_pos != -1:
                    # Reasoning before tag
                    if close_pos > 0:
                        reasoning_out.append(self.buffer[:close_pos])
                    self.buffer = self.buffer[close_pos + len(self.CLOSE_TAG):]
                    self.state = StreamingParserState.OUTSIDE_THINK
                else:
                    # Check if buffer ends with a partial prefix of CLOSE_TAG
                    tail_len = 0
                    for i in range(len(self.CLOSE_TAG) - 1, 0, -1):
                        if self.buffer.endswith(self.CLOSE_TAG[:i]):
                            tail_len = i
                            break
                    if tail_len > 0:
                        prefix = self.buffer[:-tail_len]
                        if prefix:
                            reasoning_out.append(prefix)
                        self.buffer = self.buffer[-tail_len:]
                        break
                    else:
                        reasoning_out.append(self.buffer)
                        self.buffer = ""

        r_delta = "".join(reasoning_out)
        c_delta = "".join(content_out)
        self.accumulated_reasoning += r_delta
        self.accumulated_content += c_delta
        return r_delta, c_delta

    def flush(self) -> Tuple[str, str]:
        """
        Flush any remaining buffer at stream end.
        Returns final (reasoning_delta, content_delta).
        """
        if not self.buffer:
            return "", ""

        rem = self.buffer
        self.buffer = ""
        if self.state == StreamingParserState.INSIDE_THINK:
            self.accumulated_reasoning += rem
            return rem, ""
        else:
            self.accumulated_content += rem
            return "", rem
