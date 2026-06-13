"""Python solution extracted from problems/0054.螺旋矩阵.md."""
from __future__ import annotations

class Solution(object):
    def spiralOrder(self, matrix):
        """
        :type matrix: List[List[int]]
        :rtype: List[int]
        """
        if len(matrix) == 0 or len(matrix[0]) == 0 : # 判定List是否为空
            return []
        row, col = len(matrix), len(matrix[0]) # 行数，列数
        loop = min(row, col) // 2 # 循环轮数
        stx, sty = 0, 0 # 起始x，y坐标
        i, j =0, 0
        count = 0  # 计数
        offset = 1  # 每轮减少的格子数
        result = [0] * (row * col)
        while loop>0 :# 左闭右开
            i, j = stx, sty
            while j < col - offset :   # 从左到右
                result[count] = matrix[i][j]
                count += 1
                j += 1  
            while i < row - offset : # 从上到下
                result[count] = matrix[i][j]
                count += 1
                i += 1
            while j>sty :  # 从右到左
                result[count] = matrix[i][j]
                count += 1
                j -= 1
            while i>stx :  # 从下到上
                result[count] = matrix[i][j]
                count += 1
                i -= 1
            stx += 1
            sty += 1
            offset += 1
            loop -= 1
        if min(row, col) % 2 == 1 :  # 判定是否需要填充多出来的一行
            i = stx
            if row < col :
                while i < stx + col - row + 1 :
                    result[count] = matrix[stx][i]
                    count += 1
                    i += 1
            else :
                while i < stx + row - col + 1 :
                    result[count] = matrix[i][stx]
                    count += 1
                    i += 1
        return result
