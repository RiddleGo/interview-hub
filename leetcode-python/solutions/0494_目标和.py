"""Python solution extracted from problems/0494.目标和.md."""
from __future__ import annotations

class Solution:


    def backtracking(self, candidates, target, total, startIndex, path, result):
        if total == target:
            result.append(path[:])  # 将当前路径的副本添加到结果中
        # 如果 sum + candidates[i] > target，则停止遍历
        for i in range(startIndex, len(candidates)):
            if total + candidates[i] > target:
                break
            total += candidates[i]
            path.append(candidates[i])
            self.backtracking(candidates, target, total, i + 1, path, result)
            total -= candidates[i]
            path.pop()

    def findTargetSumWays(self, nums: List[int], target: int) -> int:
        total = sum(nums)
        if target > total:
            return 0  # 此时没有方案
        if (target + total) % 2 != 0:
            return 0  # 此时没有方案，两个整数相加时要注意数值溢出的问题
        bagSize = (target + total) // 2  # 转化为组合总和问题，bagSize就是目标和

        # 以下是回溯法代码
        result = []
        nums.sort()  # 需要对nums进行排序
        self.backtracking(nums, bagSize, 0, 0, [], result)
        return len(result)
