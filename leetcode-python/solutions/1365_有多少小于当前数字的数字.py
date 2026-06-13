"""Python solution extracted from problems/1365.有多少小于当前数字的数字.md."""
from __future__ import annotations

class Solution:
    def smallerNumbersThanCurrent(self, nums: List[int]) -> List[int]:
        res = [0 for _ in range(len(nums))]
        for i in range(len(nums)):
            cnt = 0
            for j in range(len(nums)):
                if j == i:
                    continue
                if nums[i] > nums[j]:
                    cnt += 1
            res[i] = cnt
        return res
