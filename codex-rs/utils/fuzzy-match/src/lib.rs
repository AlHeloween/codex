//! # Fuzzy Match Utility
//!
//! This module provides a simple case-insensitive subsequence matcher used for
//! fuzzy filtering in various parts of the Codex TUI, such as skill search and
//! slash command filtering.
//!
//! ## Architecture
//!
//! The fuzzy matcher is a low-level utility designed to be fast and Unicode-aware.
//! It is decoupled from any UI logic and can be used in any context where
//! subsequence matching is required.
//!
//! ## Design Patterns
//!
//! - **Greedy Matching**: The algorithm uses a simple greedy approach to find the
//!   first occurrence of each character in the needle within the haystack.
//! - **Unicode Mapping**: To handle Unicode correctly (especially characters that
//!   expand when lowercased), it maintains an explicit mapping between normalized
//!   characters and their original source indices.

/// Performs a case-insensitive fuzzy match of a needle against a haystack.
///
/// This function determines if the characters in `needle` appear as a subsequence
/// within `haystack`, regardless of case. It returns the character indices of
/// the match and a score representing the quality of the match.
///
/// Args:
///     haystack (&str): The string to search within.
///     needle (&str): The sequence of characters to find.
///
/// Returns:
///     Option<(Vec<usize>, i32)>:
///         Some((indices, score)):
///             indices: A sorted list of unique character positions in the original haystack.
///             score: A ranking metric where smaller is better.
///         None: If no match is found.
///
/// Logic:
///     The algorithm performs a greedy subsequence search after normalizing both
///     inputs to lowercase. It maintains an internal mapping from normalized
///     character positions back to original `haystack` indices to handle Unicode
///     characters that expand during lowercasing (e.g., 'İ' expanding to 'i' + '̇').
///
/// Complexity:
///     Time Complexity: O(N + M), where N is the length of the haystack and M
///         is the length of the needle.
///     Space Complexity: O(N + M) for storing normalized characters and mappings.
///
/// Exceptions:
///     - Returns `Some((Vec::new(), i32::MAX))` if the needle is empty.
///     - Returns `None` if the needle characters do not appear in order.
///
/// Example:
///
/// ```rust
/// use codex_utils_fuzzy_match::fuzzy_match;
///
/// let (indices, score) = fuzzy_match("hello", "hl").unwrap();
/// assert_eq!(indices, vec![0, 2]);
/// ```
pub fn fuzzy_match(haystack: &str, needle: &str) -> Option<(Vec<usize>, i32)> {
    if needle.is_empty() {
        return Some((Vec::new(), i32::MAX));
    }

    let mut lowered_chars: Vec<char> = Vec::new();
    let mut lowered_to_orig_char_idx: Vec<usize> = Vec::new();
    for (orig_idx, ch) in haystack.chars().enumerate() {
        for lc in ch.to_lowercase() {
            lowered_chars.push(lc);
            lowered_to_orig_char_idx.push(orig_idx);
        }
    }

    let lowered_needle: Vec<char> = needle.to_lowercase().chars().collect();

    let mut result_orig_indices: Vec<usize> = Vec::with_capacity(lowered_needle.len());
    let mut last_lower_pos: Option<usize> = None;
    let mut cur = 0usize;
    for &nc in lowered_needle.iter() {
        let mut found_at: Option<usize> = None;
        while cur < lowered_chars.len() {
            if lowered_chars[cur] == nc {
                found_at = Some(cur);
                cur += 1;
                break;
            }
            cur += 1;
        }
        let pos = found_at?;
        result_orig_indices.push(lowered_to_orig_char_idx[pos]);
        last_lower_pos = Some(pos);
    }

    let first_lower_pos = if result_orig_indices.is_empty() {
        0usize
    } else {
        let target_orig = result_orig_indices[0];
        lowered_to_orig_char_idx
            .iter()
            .position(|&oi| oi == target_orig)
            .unwrap_or(0)
    };
    // last defaults to first for single-hit; score = extra span between first/last hit
    // minus needle len (≥0).
    // Strongly reward prefix matches by subtracting 100 when the first hit is at index 0.
    let last_lower_pos = last_lower_pos.unwrap_or(first_lower_pos);
    let window =
        (last_lower_pos as i32 - first_lower_pos as i32 + 1) - (lowered_needle.len() as i32);
    let mut score = window.max(0);
    if first_lower_pos == 0 {
        score -= 100;
    }

    result_orig_indices.sort_unstable();
    result_orig_indices.dedup();
    Some((result_orig_indices, score))
}

/// Convenience wrapper that returns only the matched indices.
///
/// Use this when the match score is not needed.
///
/// Args:
///     haystack (&str): The string to search within.
///     needle (&str): The sequence of characters to find.
///
/// Returns:
///     Option<Vec<usize>>: Sorted list of indices if matched, else None.
///
/// Example:
///
/// ```rust
/// use codex_utils_fuzzy_match::fuzzy_indices;
///
/// let indices = fuzzy_indices("hello", "hl").unwrap();
/// assert_eq!(indices, vec![0, 2]);
/// ```
pub fn fuzzy_indices(haystack: &str, needle: &str) -> Option<Vec<usize>> {
    fuzzy_match(haystack, needle).map(|(mut idx, _)| {
        idx.sort_unstable();
        idx.dedup();
        idx
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ascii_basic_indices() {
        let (idx, score) = match fuzzy_match("hello", "hl") {
            Some(v) => v,
            None => panic!("expected a match"),
        };
        assert_eq!(idx, vec![0, 2]);
        // 'h' at 0, 'l' at 2 -> window 1; start-of-string bonus applies (-100)
        assert_eq!(score, -99);
    }

    #[test]
    fn unicode_dotted_i_istanbul_highlighting() {
        let (idx, score) = match fuzzy_match("İstanbul", "is") {
            Some(v) => v,
            None => panic!("expected a match"),
        };
        assert_eq!(idx, vec![0, 1]);
        // Matches at lowered positions 0 and 2 -> window 1; start-of-string bonus applies
        assert_eq!(score, -99);
    }

    #[test]
    fn unicode_german_sharp_s_casefold() {
        assert!(fuzzy_match("straße", "strasse").is_none());
    }

    #[test]
    fn prefer_contiguous_match_over_spread() {
        let (_idx_a, score_a) = match fuzzy_match("abc", "abc") {
            Some(v) => v,
            None => panic!("expected a match"),
        };
        let (_idx_b, score_b) = match fuzzy_match("a-b-c", "abc") {
            Some(v) => v,
            None => panic!("expected a match"),
        };
        // Contiguous window -> 0; start-of-string bonus -> -100
        assert_eq!(score_a, -100);
        // Spread over 5 chars for 3-letter needle -> window 2; with bonus -> -98
        assert_eq!(score_b, -98);
        assert!(score_a < score_b);
    }

    #[test]
    fn start_of_string_bonus_applies() {
        let (_idx_a, score_a) = match fuzzy_match("file_name", "file") {
            Some(v) => v,
            None => panic!("expected a match"),
        };
        let (_idx_b, score_b) = match fuzzy_match("my_file_name", "file") {
            Some(v) => v,
            None => panic!("expected a match"),
        };
        // Start-of-string contiguous -> window 0; bonus -> -100
        assert_eq!(score_a, -100);
        // Non-prefix contiguous -> window 0; no bonus -> 0
        assert_eq!(score_b, 0);
        assert!(score_a < score_b);
    }

    #[test]
    fn empty_needle_matches_with_max_score_and_no_indices() {
        let (idx, score) = match fuzzy_match("anything", "") {
            Some(v) => v,
            None => panic!("empty needle should match"),
        };
        assert!(idx.is_empty());
        assert_eq!(score, i32::MAX);
    }

    #[test]
    fn case_insensitive_matching_basic() {
        let (idx, score) = match fuzzy_match("FooBar", "foO") {
            Some(v) => v,
            None => panic!("expected a match"),
        };
        assert_eq!(idx, vec![0, 1, 2]);
        // Contiguous prefix match (case-insensitive) -> window 0 with bonus
        assert_eq!(score, -100);
    }

    #[test]
    fn indices_are_deduped_for_multichar_lowercase_expansion() {
        let needle = "\u{0069}\u{0307}"; // "i" + combining dot above
        let (idx, score) = match fuzzy_match("İ", needle) {
            Some(v) => v,
            None => panic!("expected a match"),
        };
        assert_eq!(idx, vec![0]);
        // Lowercasing 'İ' expands to two chars; contiguous prefix -> window 0 with bonus
        assert_eq!(score, -100);
    }
}
