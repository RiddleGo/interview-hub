"""Python solution extracted from problems/kamacoder/0097.小明逛公园.md."""
from __future__ import annotations

if __name__ == '__main__':
    max_int = 10005  # 设置最大路径，因为边最大距离为10^4

    n, m = map(int, input().split())

    grid = [[[max_int] * (n+1) for _ in range(n+1)] for _ in range(n+1)]  # 初始化三维dp数组

    for _ in range(m):
        p1, p2, w = map(int, input().split())
        grid[p1][p2][0] = w
        grid[p2][p1][0] = w

    # 开始floyd
    for k in range(1, n+1):
        for i in range(1, n+1):
            for j in range(1, n+1):
                grid[i][j][k] = min(grid[i][j][k-1], grid[i][k][k-1] + grid[k][j][k-1])

    # 输出结果
    z = int(input())
    for _ in range(z):
        start, end = map(int, input().split())
        if grid[start][end][n] == max_int:
            print(-1)
        else:
            print(grid[start][end][n])
