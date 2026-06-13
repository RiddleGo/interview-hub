"""Python solution extracted from problems/0724.寻找数组的中心索引.md."""
from __future__ import annotations

class Solution:
    def pivotIndex(self, nums: List[int]) -> int:
        numSum = sum(nums) #数组总和
        leftSum = 0
        for i in range(len(nums)):
            if numSum - leftSum -nums[i] == leftSum: #左右和相等
                return i
            leftSum += nums[i]
        return -1
