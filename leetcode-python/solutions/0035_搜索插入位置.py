"""Python solution extracted from problems/0035.搜索插入位置.md."""
from __future__ import annotations

# 第一种二分法: [left, right]左闭右闭区间
class Solution:
    def searchInsert(self, nums: List[int], target: int) -> int:
        left, right = 0, len(nums) - 1

        while left <= right:
            middle = (left + right) // 2

            if nums[middle] < target:
                left = middle + 1
            elif nums[middle] > target:
                right = middle - 1
            else:
                return middle
        return right + 1
