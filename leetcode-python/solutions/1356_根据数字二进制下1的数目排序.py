"""Python solution extracted from problems/1356.根据数字二进制下1的数目排序.md."""
from __future__ import annotations

class Solution:
    def sortByBits(self, arr: List[int]) -> List[int]:
        arr.sort(key=lambda num: (self.count_bits(num), num))
        return arr

    def count_bits(self, num: int) -> int:
        count = 0
        while num:
            num &= num - 1
            count += 1
        return count
