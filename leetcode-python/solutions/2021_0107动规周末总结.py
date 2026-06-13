"""Python solution extracted from problems/周总结/20210107动规周末总结.md."""
from __future__ import annotations

"""Auto-generated placeholder converted from `cpp`.
Source: problems\周总结\20210107动规周末总结.md
Manual rewrite may be required for algorithm equivalence.
"""

from typing import Any


def solve(*args: Any, **kwargs: Any) -> Any:
    """
    TODO: Replace this placeholder with a real Python implementation.
    Original source is preserved in ORIGINAL_SNIPPET.
    """
    raise NotImplementedError("Auto-generated placeholder; implement in Python")


ORIGINAL_SNIPPET = """
dp[1] = 1;
dp[2] = 2;
for (int i = 3; i <= n; i++) { // 注意i是从3开始的
    dp[i] = dp[i - 1] + dp[i - 2];
}
"""
