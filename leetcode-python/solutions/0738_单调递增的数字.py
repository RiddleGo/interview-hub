"""Python solution extracted from problems/0738.单调递增的数字.md."""
from __future__ import annotations

class Solution:
    def checkNum(self, num):
        max_digit = 10
        while num:
            digit = num % 10
            if max_digit >= digit:
                max_digit = digit
            else:
                return False
            num //= 10
        return True

    def monotoneIncreasingDigits(self, N):
        for i in range(N, 0, -1):
            if self.checkNum(i):
                return i
        return 0
