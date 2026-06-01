"""Python solution extracted from problems/背包问题理论基础多重背包.md."""
from __future__ import annotations

C, N = input().split(" ")
C, N = int(C), int(N)

# value数组需要判断一下非空不然过不了
weights = [int(x) for x in input().split(" ")]
values = [int(x) for x in input().split(" ") if x]
nums = [int(x) for x in input().split(" ")]

dp = [0] * (C + 1)
# 遍历背包容量
for i in range(N):
    for j in range(C, weights[i] - 1, -1):
        for k in range(1, nums[i] + 1):
            # 遍历 k，如果已经大于背包容量直接跳出循环
            if k * weights[i] > j:
                break
            dp[j] = max(dp[j], dp[j - weights[i] * k] + values[i] * k) 
print(dp[-1])
