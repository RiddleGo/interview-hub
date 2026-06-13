"""Python solution extracted from problems/周总结/20201224贪心周末总结.md."""
from __future__ import annotations

"""Auto-generated placeholder converted from `cpp`.
Source: problems\周总结\20201224贪心周末总结.md
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
    // 按照区间左边界从大到小排序
    static bool cmp (const vector<int>& a, const vector<int>& b) {
        return a[0] < b[0];
    }
    int eraseOverlapIntervals(vector<vector<int>>& intervals) {
        if (intervals.size() == 0) return 0;
        sort(intervals.begin(), intervals.end(), cmp);

        int result = 1;
        for (int i = 1; i < intervals.size(); i++) {
            if (intervals[i][0] >= intervals[i - 1][1]) { // 需要要把> 改成 >= 就可以了
                result++; // 需要一支箭
            }
            else {
                intervals[i][1] = min(intervals[i - 1][1], intervals[i][1]); // 更新重叠气球最小右边界
            }
        }
        return intervals.size() - result;
    }
};
"""
