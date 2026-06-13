"""Python solution extracted from problems/背包问题理论基础完全背包.md."""
from __future__ import annotations

def knapsack(n, bag_weight, weight, value):
    dp = [[0] * (bag_weight + 1) for _ in range(n)]

    # 初始化
    for j in range(weight[0], bag_weight + 1):
        dp[0][j] = dp[0][j - weight[0]] + value[0]

    # 动态规划
    for i in range(1, n):
        for j in range(bag_weight + 1):
            if j < weight[i]:
                dp[i][j] = dp[i - 1][j]
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - weight[i]] + value[i])

    return dp[n - 1][bag_weight]

# 输入
n, bag_weight = map(int, input().split())
weight = []
value = []
for _ in range(n):
    w, v = map(int, input().split())
    weight.append(w)
    value.append(v)

# 输出结果
print(knapsack(n, bag_weight, weight, value))
