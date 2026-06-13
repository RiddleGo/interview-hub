"""Python solution extracted from problems/kamacoder/0101.孤岛的总面积.md."""
from __future__ import annotations

position = [[1, 0], [0, 1], [-1, 0], [0, -1]]
count = 0

def dfs(grid, x, y):
    global count
    grid[x][y] = 0
    count += 1
    for i, j in position:
        next_x = x + i
        next_y = y + j
        if next_x < 0 or next_y < 0 or next_x >= len(grid) or next_y >= len(grid[0]):
            continue
        if grid[next_x][next_y] == 1: 
            dfs(grid, next_x, next_y)
                
n, m = map(int, input().split())

# 邻接矩阵
grid = []
for i in range(n):
    grid.append(list(map(int, input().split())))

# 清除边界上的连通分量
for i in range(n):
    if grid[i][0] == 1: 
        dfs(grid, i, 0)
    if grid[i][m - 1] == 1: 
        dfs(grid, i, m - 1)

for j in range(m):
    if grid[0][j] == 1: 
        dfs(grid, 0, j)
    if grid[n - 1][j] == 1: 
        dfs(grid, n - 1, j)
    
count = 0 # 将count重置为0
# 统计内部所有剩余的连通分量
for i in range(n):
    for j in range(m):
        if grid[i][j] == 1:
            dfs(grid, i, j)
            
print(count)
