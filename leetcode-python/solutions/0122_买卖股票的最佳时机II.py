"""Python solution extracted from problems/0122.买卖股票的最佳时机II.md."""
from __future__ import annotations

class Solution:
    def maxProfit(self, prices: List[int]) -> int:
        result = 0
        for i in range(1, len(prices)):
            result += max(prices[i] - prices[i - 1], 0)
        return result
