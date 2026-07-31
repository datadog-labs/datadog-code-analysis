#!/usr/bin/env python3
# Unless explicitly stated otherwise all files in this repository are licensed under the Apache-2.0 License.
# This product includes software developed at Datadog (https://www.datadoghq.com/) Copyright 2026 Datadog, Inc.

import unittest
from unittest.mock import patch

from reviewer import DIFF_EXCLUDE_PATHSPECS, claim_review
from core.state.session_state import ReadWriteSessionState, ro_session_state, rw_session_state

CASES: list = [
    (
        "nothing committed yet -- no diff, don't claim",
        {},
        "head1",
        "",
        None,
        {},
    ),
    (
        "non-empty diff -- claim review",
        {"baseline_sha": "base1"},
        "head1",
        "diff content",
        "diff content",
        {"baseline_sha": "base1", "review_done": True, "review_sha": "head1"},
    ),
    (
        "no baseline_sha recorded -- falls back to head as baseline",
        {},
        "head1",
        "diff content",
        "diff content",
        {"review_done": True, "review_sha": "head1"},
    ),
    (
        "already claimed -- second caller gets nothing",
        {"review_done": True, "review_sha": "head1"},
        "head1",
        "",
        None,
        {"review_done": True, "review_sha": "head1"},
    ),
]


class ClaimReviewTest(unittest.TestCase):
    def test_cases(self):
        for description, data, head, diff, expected_diff, expected_data in CASES:
            with self.subTest(description):
                state = ReadWriteSessionState(dict(data))
                with patch("reviewer.repo.diff", return_value=diff):
                    result = claim_review(state, "/repo", head)
                self.assertEqual(result, expected_diff)
                self.assertEqual(state._data, expected_data)

    def test_uses_baseline_sha_when_present(self):
        state = ReadWriteSessionState({"baseline_sha": "base1"})
        with patch("reviewer.repo.diff", return_value="diff") as mock_diff:
            claim_review(state, "/repo", "head1")
        mock_diff.assert_called_once_with("/repo", "base1", "head1", DIFF_EXCLUDE_PATHSPECS)

    def test_falls_back_to_head_when_no_baseline_sha(self):
        state = ReadWriteSessionState({})
        with patch("reviewer.repo.diff", return_value="diff") as mock_diff:
            claim_review(state, "/repo", "head1")
        mock_diff.assert_called_once_with("/repo", "head1", "head1", DIFF_EXCLUDE_PATHSPECS)

    def test_does_not_diff_once_review_done(self):
        state = ReadWriteSessionState({"review_done": True, "review_sha": "head1"})
        with patch("reviewer.repo.diff") as mock_diff:
            claim_review(state, "/repo", "head1")
        mock_diff.assert_not_called()
