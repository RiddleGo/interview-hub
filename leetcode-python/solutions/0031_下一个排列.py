"""Python solution extracted from problems/0031.下一个排列.md."""
from __future__ import annotations

class Solution:
    def nextPermutation(self, nums: List[int]) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        length = len(nums)
        for i in range(length - 2, -1, -1): # 从倒数第二个开始
            if nums[i]>=nums[i+1]: continue # 剪枝去重
            for j in range(length - 1, i, -1):
                if nums[j] > nums[i]:
                    nums[j], nums[i] = nums[i], nums[j]
                    self.reverse(nums, i + 1, length - 1)
                    return  
        self.reverse(nums, 0, length - 1)
    
    def reverse(self, nums: List[int], left: int, right: int) -> None:
        while left < right:
            nums[left], nums[right] = nums[right], nums[left]
            left += 1
            right -= 1
            
"""
265 / 265 个通过测试用例
状态：通过
执行用时: 36 ms
内存消耗: 14.9 MB
"""
