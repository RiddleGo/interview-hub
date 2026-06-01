"""Python solution extracted from problems/背包问题完全背包一维.md."""
from __future__ import annotations

def complete_knapsack(N, bag_weight, weight, value):
    dp = [0] * (bag_weight + 1)

    for j in range(bag_weight + 1):  # 遍历背包容量
        for i in range(len(weight)):  # 遍历物品
            if j >= weight[i]:
                dp[j] = max(dp[j], dp[j - weight[i]] + value[i])

    return dp[bag_weight]

# 输入
N, bag_weight = map(int, input().split())
weight = []
value = []
for _ in range(N):
    w, v = map(int, input().split())
    weight.append(w)
    value.append(v)

# 输出结果
print(complete_knapsack(N, bag_weight, weight, value))
