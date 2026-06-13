"""Python solution extracted from problems/kamacoder/0104.建造最大岛屿.md."""
from __future__ import annotations

from typing import List
from collections import defaultdict

class Solution:
    def __init__(self):
        self.direction = [(1,0),(-1,0),(0,1),(0,-1)]
        self.res = 0
        self.count = 0
        self.idx = 1
        self.count_area = defaultdict(int)

    def max_area_island(self, grid: List[List[int]]) -> int:
        if not grid or len(grid) == 0 or len(grid[0]) == 0:
            return 0

        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == 1:
                    self.count = 0
                    self.idx += 1
                    self.dfs(grid,i,j)
        # print(grid)
        self.check_area(grid)
        # print(self.count_area)
        
        if self.check_largest_connect_island(grid=grid):
            return self.res + 1
        return max(self.count_area.values())
    
    def dfs(self,grid,row,col):
        grid[row][col] = self.idx
        self.count += 1
        for dr,dc in self.direction:
            _row = dr + row 
            _col = dc + col 
            if 0<=_row<len(grid) and 0<=_col<len(grid[0]) and grid[_row][_col] == 1:
                self.dfs(grid,_row,_col)
        return

    def check_area(self,grid):
        m, n = len(grid), len(grid[0])
        for row in range(m):
            for col in range(n):
                  self.count_area[grid[row][col]] = self.count_area.get(grid[row][col],0) + 1
        return

    def check_largest_connect_island(self,grid):
        m, n = len(grid), len(grid[0])
        has_connect = False
        for row in range(m):
            for col in range(n):
                if grid[row][col] == 0:
                    has_connect = True
                    area = 0
                    visited = set()
                    for dr, dc in self.direction:
                        _row = row + dr 
                        _col = col + dc
                        if 0<=_row<len(grid) and 0<=_col<len(grid[0]) and grid[_row][_col] != 0 and grid[_row][_col] not in visited:
                            visited.add(grid[_row][_col])
                            area += self.count_area[grid[_row][_col]]
                            self.res = max(self.res, area)
                            
        return has_connect




def main():
    m, n = map(int, input().split())
    grid = []

    for i in range(m):
        grid.append(list(map(int,input().split())))

    
    sol = Solution()
    print(sol.max_area_island(grid))

if __name__ == '__main__':
    main()
