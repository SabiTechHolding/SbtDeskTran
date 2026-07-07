"""
Diff Engine - computes word-level and line-level diffs
similar to GitHub / VSCode / Beyond Compare style.
Supports CJK (Japanese, Chinese, Korean) character-level tokenization.
"""
import difflib
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class DiffChunk:
    """Represents a chunk of diff."""
    kind: str          # 'equal' | 'insert' | 'delete' | 'replace'
    old_lines: List[str] = field(default_factory=list)
    new_lines: List[str] = field(default_factory=list)
    old_start: int = 0
    new_start: int = 0


@dataclass
class InlineToken:
    """Word-level token within a changed line."""
    text: str
    kind: str   # 'equal' | 'insert' | 'delete'


# CJK codepoint ranges — check bằng ord() nhanh hơn regex
_CJK_RANGES = (
    (0x3000, 0x303f),   # CJK symbols & punctuation
    (0x3040, 0x309f),   # Hiragana
    (0x30a0, 0x30ff),   # Katakana
    (0x31f0, 0x31ff),   # Katakana phonetic extensions
    (0xff00, 0xffef),   # Halfwidth/fullwidth forms
    (0x4e00, 0x9fff),   # CJK Unified Ideographs
    (0x3400, 0x4dbf),   # CJK Extension A
    (0x20000, 0x2a6df), # CJK Extension B
    (0xac00, 0xd7af),   # Hangul syllables
    (0x1100, 0x11ff),   # Hangul Jamo
    (0xa960, 0xa97f),   # Hangul Jamo Extended-A
    (0xd7b0, 0xd7ff),   # Hangul Jamo Extended-B
)


def _is_cjk_char(ch: str) -> bool:
    """Return True if character belongs to a CJK/Hangul script."""
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _CJK_RANGES)


def tokenize_inline(line: str) -> List[str]:
    """
    Smart tokenizer:
    - CJK scripts (Japanese, Chinese, Korean): each character is a separate token
    - Latin / other scripts: words kept together (split on whitespace)
    - Mixed lines handled correctly
    """
    tokens: List[str] = []
    buf = ""        # accumulates non-CJK non-space chars

    for ch in line:
        if ch in (" ", "\t"):
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)
        elif _is_cjk_char(ch):
            if buf:
                tokens.append(buf)
                buf = ""
            tokens.append(ch)   # each CJK char is its own token
        else:
            buf += ch           # accumulate Latin / other chars into a word

    if buf:
        tokens.append(buf)

    return tokens


def compute_line_diff(old_text: str, new_text: str) -> List[DiffChunk]:
    """Compute line-by-line diff between two texts."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    if old_lines and not old_lines[-1].endswith("\n"):
        old_lines[-1] += "\n"
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    chunks: List[DiffChunk] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        chunks.append(DiffChunk(
            kind=tag,
            old_lines=old_lines[i1:i2],
            new_lines=new_lines[j1:j2],
            old_start=i1,
            new_start=j1,
        ))

    return chunks


def compute_inline_diff(
    old_line: str, new_line: str
) -> Tuple[List[InlineToken], List[InlineToken]]:
    """Compute token-level inline diff for a pair of changed lines."""
    old_tokens = tokenize_inline(old_line.rstrip("\n"))
    new_tokens = tokenize_inline(new_line.rstrip("\n"))

    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)

    old_result: List[InlineToken] = []
    new_result: List[InlineToken] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for t in old_tokens[i1:i2]:
                old_result.append(InlineToken(t, "equal"))
            for t in new_tokens[j1:j2]:
                new_result.append(InlineToken(t, "equal"))
        elif tag == "insert":
            for t in new_tokens[j1:j2]:
                new_result.append(InlineToken(t, "insert"))
        elif tag == "delete":
            for t in old_tokens[i1:i2]:
                old_result.append(InlineToken(t, "delete"))
        elif tag == "replace":
            for t in old_tokens[i1:i2]:
                old_result.append(InlineToken(t, "delete"))
            for t in new_tokens[j1:j2]:
                new_result.append(InlineToken(t, "insert"))

    return old_result, new_result


def get_diff_stats(chunks: List[DiffChunk]) -> dict:
    """Return summary statistics for a diff."""
    added   = sum(len(c.new_lines) for c in chunks if c.kind in ("insert", "replace"))
    removed = sum(len(c.old_lines) for c in chunks if c.kind in ("delete", "replace"))
    changed = sum(1 for c in chunks if c.kind != "equal")
    return {"added": added, "removed": removed, "changed_blocks": changed}
