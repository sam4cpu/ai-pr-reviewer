"""
Unit test: ensures reviewer runs end-to-end with mocked OpenAI.
"""

import os, sys, json
from unittest import mock
import tempfile

# Adjust path to import reviewer.py
sys.path.insert(0, ".github/actions/ai_pr_reviewer")

def test_reviewer_runs_with_mock(monkeypatch):
    import reviewer

    tmp = tempfile.TemporaryDirectory()
    os.chdir(tmp.name)
    open("pr_diff.patch", "w").write("diff --git a/x b/x\n+print('test')\n")

    # Fake environment
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("PR_NUMBER", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "fake")
    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    # Mock OpenAI calls inside reviewer
    with mock.patch("reviewer.OpenAI") as MockClient:
        inst = MockClient.return_value
        inst.chat.completions.create.return_value = mock.Mock(
            choices=[mock.Mock(message=mock.Mock(content="Mocked review OK"))]
        )
        reviewer.main()

    assert os.path.exists("ai_review.md"), "ai_review.md not produced"
