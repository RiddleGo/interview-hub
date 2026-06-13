"""Python solution extracted from problems/周总结/20210128动规周末总结.md."""
from __future__ import annotations

"""Auto-generated placeholder converted from `cpp`.
Source: problems\周总结\20210128动规周末总结.md
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
// 先遍历物品，再遍历背包
for(int i = 0; i < weight.size(); i++) { // 遍历物品
    for(int j = weight[i]; j < bagWeight ; j++) { // 遍历背包容量
        dp[j] = max(dp[j], dp[j - weight[i]] + value[i]);

    }
}
"""
