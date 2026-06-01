"""Python solution extracted from problems/0053.最大子序和.md."""
from __future__ import annotations

class Solution:
    def maxSubArray(self, nums):
        result = float('-inf')  # 初始化结果为负无穷大
        count = 0
        for i in range(len(nums)):  # 设置起始位置
            count = 0
            for j in range(i, len(nums)):  # 从起始位置i开始遍历寻找最大值
                count += nums[j]
                result = max(count, result)  # 更新最大值
        return result
