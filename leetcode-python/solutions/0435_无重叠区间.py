"""Python solution extracted from problems/0435.无重叠区间.md."""
from __future__ import annotations

class Solution:
    def eraseOverlapIntervals(self, intervals: List[List[int]]) -> int:
        if not intervals:
            return 0
        
        intervals.sort(key=lambda x: x[0])  # 按照左边界升序排序
        count = 0  # 记录重叠区间数量
        
        for i in range(1, len(intervals)):
            if intervals[i][0] < intervals[i - 1][1]:  # 存在重叠区间
                intervals[i][1] = min(intervals[i - 1][1], intervals[i][1])  # 更新重叠区间的右边界
                count += 1
        
        return count
