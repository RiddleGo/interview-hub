"""Python solution extracted from problems/0070.爬楼梯完全背包版本.md."""
from __future__ import annotations

def climbing_stairs(n,m):
    dp = [0]*(n+1) # 背包总容量
    dp[0] = 1 
    # 排列题，注意循环顺序，背包在外物品在内
    for j in range(1,n+1):
        for i in range(1,m+1):
            if j>=i:
                dp[j] += dp[j-i] # 这里i就是重量而非index
    return dp[n]

if __name__ == '__main__':
    n,m = list(map(int,input().split(' ')))
    print(climbing_stairs(n,m))
