"""Python solution extracted from problems/0787.K站中转内最便宜的航班.md."""
from __future__ import annotations

"""Auto-generated placeholder converted from `cpp`.
Source: problems\0787.K站中转内最便宜的航班.md
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
    int findCheapestPrice(int n, vector<vector<int>>& flights, int src, int dst, int k) {
        vector<int> minDist(n , INT_MAX/2);
        minDist[src] = 0;
        vector<int> minDist_copy(n); // 用来记录每一次遍历的结果
        for (int i = 1; i <= k + 1; i++) {
            minDist_copy = minDist; // 获取上一次计算的结果
            for (auto &f : flights) {
                int from = f[0];
                int to = f[1];
                int price = f[2];
                minDist[to] = min(minDist_copy[from] + price, minDist[to]);
                // if (minDist[to] > minDist_copy[from] + price) minDist[to] = minDist_copy[from] + price;
            }

        }
        int result = minDist[dst] == INT_MAX/2 ? -1 : minDist[dst];
        return result;
    }
};
"""
