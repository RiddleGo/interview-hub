"""Python solution extracted from problems/回溯算法去重问题的另一种写法.md."""
from __future__ import annotations

class Solution:
    def subsetsWithDup(self, nums):
        nums.sort()  # 去重需要排序
        result = []
        self.backtracking(nums, 0, [], result)
        return result

    def backtracking(self, nums, startIndex, path, result):
        result.append(path[:])
        used = set()
        for i in range(startIndex, len(nums)):
            if nums[i] in used:
                continue
            used.add(nums[i])
            path.append(nums[i])
            self.backtracking(nums, i + 1, path, result)
            path.pop()
