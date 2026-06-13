"""Python solution extracted from problems/前序/代码风格.md."""
from __future__ import annotations

"""Auto-generated placeholder converted from `cpp`.
Source: problems\前序\代码风格.md
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
class Solution {
public:
    void moveZeroes(vector<int>& nums) {
        int slowIndex = 0;
        for (int fastIndex = 0; fastIndex < nums.size(); fastIndex++) {
            if (nums[fastIndex] != 0) {
                nums[slowIndex++] = nums[fastIndex];
            }
        }
        for (int i = slowIndex; i < nums.size(); i++) {
            nums[i] = 0;
        }
    }
};
"""
