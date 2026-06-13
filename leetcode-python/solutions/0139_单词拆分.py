"""Python solution extracted from problems/0139.单词拆分.md."""
from __future__ import annotations

class Solution:
    def backtracking(self, s: str, wordSet: set[str], startIndex: int) -> bool:
        # 边界情况：已经遍历到字符串末尾，返回True
        if startIndex >= len(s):
            return True

        # 遍历所有可能的拆分位置
        for i in range(startIndex, len(s)):
            word = s[startIndex:i + 1]  # 截取子串
            if word in wordSet and self.backtracking(s, wordSet, i + 1):
                # 如果截取的子串在字典中，并且后续部分也可以被拆分成单词，返回True
                return True

        # 无法进行有效拆分，返回False
        return False

    def wordBreak(self, s: str, wordDict: List[str]) -> bool:
        wordSet = set(wordDict)  # 转换为哈希集合，提高查找效率
        return self.backtracking(s, wordSet, 0)
