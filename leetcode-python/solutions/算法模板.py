"""Python solution extracted from problems/算法模板.md."""
from __future__ import annotations

def binarysearch(nums, target):
    low = 0
    high = len(nums) - 1
    while (low <= high):
        mid = (high + low)//2

        if (nums[mid] < target):
            low = mid + 1
            
        if (nums[mid] > target):
            high = mid - 1
            
        if (nums[mid] == target):
            return mid

    return -1
