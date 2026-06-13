"""Python solution extracted from problems/0941.有效的山脉数组.md."""
from __future__ import annotations

class Solution:
    def validMountainArray(self, arr: List[int]) -> bool:
        left, right = 0, len(arr)-1
        
        while left < len(arr)-1 and arr[left+1] > arr[left]:
            left += 1
        
        while right > 0 and arr[right-1] > arr[right]:
            right -= 1
        
        return left == right and right != 0 and left != len(arr)-1
