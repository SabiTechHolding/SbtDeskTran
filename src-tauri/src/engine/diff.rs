use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum SequenceTag {
    Equal,
    Delete,
    Insert,
    Replace,
}

type SequenceOpcode = (SequenceTag, std::ops::Range<usize>, std::ops::Range<usize>);

// This longest-match strategy keeps repeated lines/tokens aligned consistently.
// `similar::TextDiff` uses Myers and can choose a different alignment, which
// changes block counts and the visual regions shown to the user.
fn longest_match<T: PartialEq>(
    old: &[T],
    new: &[T],
    old_start: usize,
    old_end: usize,
    new_start: usize,
    new_end: usize,
) -> (usize, usize, usize) {
    let mut previous = vec![0usize; new_end.saturating_sub(new_start)];
    let mut best = (old_start, new_start, 0usize);
    for (old_index, old_value) in old.iter().enumerate().take(old_end).skip(old_start) {
        let mut current = vec![0usize; previous.len()];
        for (new_index, new_value) in new.iter().enumerate().take(new_end).skip(new_start) {
            if old_value == new_value {
                let offset = new_index - new_start;
                let length = if offset == 0 {
                    1
                } else {
                    previous[offset - 1] + 1
                };
                current[offset] = length;
                if length > best.2 {
                    best = (old_index + 1 - length, new_index + 1 - length, length);
                }
            }
        }
        previous = current;
    }
    best
}

fn sequence_opcodes<T: PartialEq>(old: &[T], new: &[T]) -> Vec<SequenceOpcode> {
    let mut pending = vec![(0usize, old.len(), 0usize, new.len())];
    let mut blocks = Vec::new();
    while let Some((old_start, old_end, new_start, new_end)) = pending.pop() {
        let (old_match, new_match, size) =
            longest_match(old, new, old_start, old_end, new_start, new_end);
        if size == 0 {
            continue;
        }
        if old_start < old_match && new_start < new_match {
            pending.push((old_start, old_match, new_start, new_match));
        }
        if old_match + size < old_end && new_match + size < new_end {
            pending.push((old_match + size, old_end, new_match + size, new_end));
        }
        blocks.push((old_match, new_match, size));
    }
    blocks.sort_unstable_by_key(|(old_start, new_start, _)| (*old_start, *new_start));
    let mut merged_blocks: Vec<(usize, usize, usize)> = Vec::with_capacity(blocks.len());
    for block in blocks {
        if let Some(previous) = merged_blocks.last_mut() {
            if previous.0 + previous.2 == block.0 && previous.1 + previous.2 == block.1 {
                previous.2 += block.2;
                continue;
            }
        }
        merged_blocks.push(block);
    }

    let mut opcodes = Vec::new();
    let mut old_cursor = 0;
    let mut new_cursor = 0;
    for (old_match, new_match, size) in merged_blocks {
        if old_cursor < old_match || new_cursor < new_match {
            let tag = match (old_match - old_cursor, new_match - new_cursor) {
                (0, _) => SequenceTag::Insert,
                (_, 0) => SequenceTag::Delete,
                _ => SequenceTag::Replace,
            };
            opcodes.push((tag, old_cursor..old_match, new_cursor..new_match));
        }
        opcodes.push((
            SequenceTag::Equal,
            old_match..old_match + size,
            new_match..new_match + size,
        ));
        old_cursor = old_match + size;
        new_cursor = new_match + size;
    }
    if old_cursor < old.len() || new_cursor < new.len() {
        let tag = match (old.len() - old_cursor, new.len() - new_cursor) {
            (0, _) => SequenceTag::Insert,
            (_, 0) => SequenceTag::Delete,
            _ => SequenceTag::Replace,
        };
        opcodes.push((tag, old_cursor..old.len(), new_cursor..new.len()));
    }
    opcodes
}

#[derive(Debug, Serialize, Clone)]
pub struct InlineToken {
    pub text: String,
    pub kind: String,
}

#[derive(Debug, Serialize)]
pub struct DiffLine {
    pub kind: String,
    pub left_text: String,
    pub right_text: String,
    pub left_present: bool,
    pub right_present: bool,
    pub left_tokens: Vec<InlineToken>,
    pub right_tokens: Vec<InlineToken>,
}

#[derive(Debug, Serialize)]
pub struct DiffResult {
    pub lines: Vec<DiffLine>,
    pub added: usize,
    pub removed: usize,
    pub changed_blocks: usize,
}

fn is_cjk_char(character: char) -> bool {
    matches!(
        character as u32,
        0x3000..=0x303f
            | 0x3040..=0x309f
            | 0x30a0..=0x30ff
            | 0x31f0..=0x31ff
            | 0xff00..=0xffef
            | 0x4e00..=0x9fff
            | 0x3400..=0x4dbf
            | 0x20000..=0x2a6df
            | 0xac00..=0xd7af
            | 0x1100..=0x11ff
            | 0xa960..=0xa97f
            | 0xd7b0..=0xd7ff
    )
}

fn tokenize_inline(line: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut word = String::new();

    for character in line.chars() {
        if is_cjk_char(character) {
            if !word.is_empty() {
                tokens.push(std::mem::take(&mut word));
            }
            tokens.push(character.to_string());
        } else if character == '_' || character.is_alphanumeric() {
            word.push(character);
        } else {
            if !word.is_empty() {
                tokens.push(std::mem::take(&mut word));
            }
            tokens.push(character.to_string());
        }
    }

    if !word.is_empty() {
        tokens.push(word);
    }
    tokens
}

fn push_token(tokens: &mut Vec<InlineToken>, text: &str, kind: &str) {
    if text.is_empty() {
        return;
    }
    if let Some(last) = tokens.last_mut() {
        if last.kind == kind {
            last.text.push_str(text);
            return;
        }
    }
    tokens.push(InlineToken {
        text: text.to_string(),
        kind: kind.to_string(),
    });
}

fn append_char_diff(
    old_text: &str,
    new_text: &str,
    old_result: &mut Vec<InlineToken>,
    new_result: &mut Vec<InlineToken>,
) {
    let old_chars: Vec<char> = old_text.chars().collect();
    let new_chars: Vec<char> = new_text.chars().collect();
    for (tag, old_range, new_range) in sequence_opcodes(&old_chars, &new_chars) {
        match tag {
            SequenceTag::Equal => {
                let text: String = old_chars[old_range].iter().collect();
                push_token(old_result, &text, "equal");
                push_token(new_result, &text, "equal");
            }
            SequenceTag::Delete => {
                let text: String = old_chars[old_range].iter().collect();
                push_token(old_result, &text, "delete");
            }
            SequenceTag::Insert => {
                let text: String = new_chars[new_range].iter().collect();
                push_token(new_result, &text, "insert");
            }
            SequenceTag::Replace => {
                let old_value: String = old_chars[old_range].iter().collect();
                let new_value: String = new_chars[new_range].iter().collect();
                push_token(old_result, &old_value, "delete");
                push_token(new_result, &new_value, "insert");
            }
        }
    }
}

fn can_char_diff_token(token: &str) -> bool {
    !token.is_empty() && !token.chars().all(char::is_whitespace) && !token.chars().any(is_cjk_char)
}

fn compute_inline_tokens(
    old_line: &str,
    new_line: &str,
    word_diff: bool,
) -> (Vec<InlineToken>, Vec<InlineToken>) {
    let old_tokens = tokenize_inline(old_line);
    let new_tokens = tokenize_inline(new_line);
    let mut old_result = Vec::new();
    let mut new_result = Vec::new();

    for (tag, old_range, new_range) in sequence_opcodes(&old_tokens, &new_tokens) {
        match tag {
            SequenceTag::Equal => {
                for token in &old_tokens[old_range] {
                    push_token(&mut old_result, token, "equal");
                }
                for token in &new_tokens[new_range] {
                    push_token(&mut new_result, token, "equal");
                }
            }
            SequenceTag::Delete => {
                for token in &old_tokens[old_range] {
                    push_token(&mut old_result, token, "delete");
                }
            }
            SequenceTag::Insert => {
                for token in &new_tokens[new_range] {
                    push_token(&mut new_result, token, "insert");
                }
            }
            SequenceTag::Replace => {
                let old_slice = &old_tokens[old_range];
                let new_slice = &new_tokens[new_range];
                if !word_diff
                    && old_slice.len() == 1
                    && new_slice.len() == 1
                    && can_char_diff_token(&old_slice[0])
                    && can_char_diff_token(&new_slice[0])
                {
                    append_char_diff(
                        &old_slice[0],
                        &new_slice[0],
                        &mut old_result,
                        &mut new_result,
                    );
                } else {
                    for token in old_slice {
                        push_token(&mut old_result, token, "delete");
                    }
                    for token in new_slice {
                        push_token(&mut new_result, token, "insert");
                    }
                }
            }
        }
    }
    (old_result, new_result)
}

fn canonicalize_line_endings(text: &str) -> String {
    text.replace("\r\n", "\n").replace('\r', "\n")
}

fn split_lines(text: &str) -> Vec<String> {
    let canonical = canonicalize_line_endings(text);
    if canonical.is_empty() {
        return Vec::new();
    }

    canonical
        .split_inclusive('\n')
        .map(|line| {
            if line.ends_with('\n') {
                line.to_string()
            } else {
                format!("{line}\n")
            }
        })
        .collect()
}

fn normalize_whitespace(line: &str) -> String {
    line.split_whitespace().collect::<Vec<_>>().join(" ")
}

fn display_line(line: Option<&String>) -> String {
    line.map(|value| value.trim_end_matches('\n').to_string())
        .unwrap_or_default()
}

fn make_line(
    kind: &str,
    left_text: String,
    right_text: String,
    left_present: bool,
    right_present: bool,
    word_diff: bool,
) -> DiffLine {
    let (left_tokens, right_tokens) = if kind == "equal" {
        (
            vec![InlineToken {
                text: left_text.clone(),
                kind: "equal".into(),
            }],
            vec![InlineToken {
                text: right_text.clone(),
                kind: "equal".into(),
            }],
        )
    } else {
        compute_inline_tokens(&left_text, &right_text, word_diff)
    };

    DiffLine {
        kind: kind.to_string(),
        left_text,
        right_text,
        left_present,
        right_present,
        left_tokens,
        right_tokens,
    }
}

pub fn compute_diff(
    left: &str,
    right: &str,
    ignore_whitespace: bool,
    word_diff: bool,
) -> Result<DiffResult, String> {
    let left_lines = split_lines(left);
    let right_lines = split_lines(right);
    let left_compare = if ignore_whitespace {
        left_lines
            .iter()
            .map(|line| normalize_whitespace(line))
            .collect::<Vec<_>>()
    } else {
        left_lines.clone()
    };
    let right_compare = if ignore_whitespace {
        right_lines
            .iter()
            .map(|line| normalize_whitespace(line))
            .collect::<Vec<_>>()
    } else {
        right_lines.clone()
    };
    let mut lines = Vec::new();
    let mut added = 0;
    let mut removed = 0;
    let mut changed_blocks = 0;

    for (tag, old_range, new_range) in sequence_opcodes(&left_compare, &right_compare) {
        match tag {
            SequenceTag::Equal => {
                for offset in 0..old_range.len() {
                    lines.push(make_line(
                        "equal",
                        display_line(left_lines.get(old_range.start + offset)),
                        display_line(right_lines.get(new_range.start + offset)),
                        true,
                        true,
                        word_diff,
                    ));
                }
            }
            SequenceTag::Delete => {
                changed_blocks += 1;
                removed += old_range.len();
                for index in old_range {
                    lines.push(make_line(
                        "delete",
                        display_line(left_lines.get(index)),
                        String::new(),
                        true,
                        false,
                        word_diff,
                    ));
                }
            }
            SequenceTag::Insert => {
                changed_blocks += 1;
                added += new_range.len();
                for index in new_range {
                    lines.push(make_line(
                        "insert",
                        String::new(),
                        display_line(right_lines.get(index)),
                        false,
                        true,
                        word_diff,
                    ));
                }
            }
            SequenceTag::Replace => {
                changed_blocks += 1;
                removed += old_range.len();
                added += new_range.len();
                let pair_count = old_range.len().max(new_range.len());
                for offset in 0..pair_count {
                    let left_present = offset < old_range.len();
                    let right_present = offset < new_range.len();
                    lines.push(make_line(
                        "replace",
                        display_line(left_lines.get(old_range.start + offset)),
                        display_line(right_lines.get(new_range.start + offset)),
                        left_present,
                        right_present,
                        word_diff,
                    ));
                }
            }
        }
    }

    Ok(DiffResult {
        lines,
        added,
        removed,
        changed_blocks,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ignores_whitespace_inside_lines() {
        let result = compute_diff("hello   world\n", "hello world\n", true, true).unwrap();
        assert_eq!(result.changed_blocks, 0);
        assert_eq!(result.lines[0].left_text, "hello   world");
        assert_eq!(result.lines[0].right_text, "hello world");
    }

    #[test]
    fn ignores_line_ending_and_final_newline_differences() {
        let result = compute_diff("one\r\ntwo\r\n", "one\ntwo", false, true).unwrap();
        assert_eq!(result.changed_blocks, 0);
        assert_eq!(result.lines.len(), 2);
    }

    #[test]
    fn highlights_changed_cjk_characters() {
        let result = compute_diff("日本語", "日本人", false, true).unwrap();
        let line = &result.lines[0];
        assert_eq!(line.left_tokens[0].text, "日本");
        assert_eq!(line.left_tokens[0].kind, "equal");
        assert_eq!(line.left_tokens[1].text, "語");
        assert_eq!(line.left_tokens[1].kind, "delete");
        assert_eq!(line.right_tokens[1].text, "人");
        assert_eq!(line.right_tokens[1].kind, "insert");
    }

    #[test]
    fn refines_changed_words_to_characters_when_disabled() {
        let result = compute_diff("cat", "cut", false, false).unwrap();
        let line = &result.lines[0];
        assert_eq!(line.left_tokens[0].text, "c");
        assert_eq!(line.left_tokens[0].kind, "equal");
        assert_eq!(line.left_tokens[1].text, "a");
        assert_eq!(line.left_tokens[1].kind, "delete");
        assert_eq!(line.left_tokens[2].text, "t");
        assert_eq!(line.left_tokens[2].kind, "equal");
        assert_eq!(line.right_tokens[1].text, "u");
        assert_eq!(line.right_tokens[1].kind, "insert");
    }

    #[test]
    fn marks_unpaired_replace_lines_as_missing() {
        let result = compute_diff("one\ntwo\nthree", "changed", false, true).unwrap();
        assert!(result.lines[0].left_present);
        assert!(result.lines[0].right_present);
        assert!(result.lines[1].left_present);
        assert!(!result.lines[1].right_present);
    }

    #[test]
    fn keeps_repeated_context_lines_aligned_around_changes() {
        let result = compute_diff(
            "header\ncommon\nold body\ncommon\nfooter",
            "header\ncommon\nnew body\ncommon\nfooter",
            false,
            true,
        )
        .unwrap();

        assert_eq!(result.changed_blocks, 1);
        assert_eq!(result.added, 1);
        assert_eq!(result.removed, 1);
        assert_eq!(result.lines.len(), 5);
        assert_eq!(result.lines[0].kind, "equal");
        assert_eq!(result.lines[1].kind, "equal");
        assert_eq!(result.lines[2].kind, "replace");
        assert_eq!(result.lines[3].kind, "equal");
        assert_eq!(result.lines[4].kind, "equal");
    }
}
