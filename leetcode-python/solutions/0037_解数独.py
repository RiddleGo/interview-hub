"""Auto-sanitized placeholder after syntax validation failure."""
from typing import Any

def solve(*args: Any, **kwargs: Any) -> Any:
    raise NotImplementedError("Sanitized placeholder; manual Python rewrite required")

ORIGINAL_SNIPPET = """
\"\"\"Python solution extracted from problems/0037.解数独.md.\"\"\"
from __future__ import annotations

class Solution{
    int[] rowBit = new int[9];
    int[] colBit = new int[9];
    int[] square9Bit = new int[9];

    public void solveSudoku(char[][] board) {
        // 1 10 11
        for (int y = 0; y < board.length; y++) {
            for (int x = 0; x < board[y].length; x++) {
                int numBit = 1 << (board[y][x] - '1');
                rowBit[y] ^= numBit;
                colBit[x] ^= numBit;
                square9Bit[(y / 3) * 3 + x / 3] ^= numBit;
            }
        }
        backtrack(board, 0);
    }

    public boolean backtrack(char[][] board, int n) {
        if (n >= 81) {
            return true;
        }

        // 快速算出行列编号 n/9 n%9
        int row = n / 9;
        int col = n % 9;

        if (board[row][col] != '.') {
            return backtrack(board, n + 1);
        }

        for (char c = '1'; c <= '9'; c++) {
            int numBit = 1 << (c - '1');
            if (!isValid(numBit, row, col)) continue;
            {
                board[row][col] = c;    // 当前的数字放入到数组之中，
                rowBit[row] ^= numBit; // 第一行rowBit[0],第一个元素eg: 1 , 0^1=1,第一个元素:4, 100^1=101,...
                colBit[col] ^= numBit;
                square9Bit[(row / 3) * 3 + col / 3] ^= numBit;
            }
            if (backtrack(board, n + 1)) return true;
            {
                board[row][col] = '.';    // 不满足条件，回退成'.'
                rowBit[row] &= ~numBit; // 第一行rowBit[0],第一个元素eg: 1 , 101&=~1==>101&111111110==>100
                colBit[col] &= ~numBit;
                square9Bit[(row / 3) * 3 + col / 3] &= ~numBit;
            }
        }
        return false;
    }


    boolean isValid(int numBit, int row, int col) {
        // 左右
        if ((rowBit[row] & numBit) > 0) return false;
        // 上下
        if ((colBit[col] & numBit) > 0) return false;
        // 9宫格: 快速算出第n个九宫格,编号[0,8] , 编号=(row / 3) * 3 + col / 3
        if ((square9Bit[(row / 3) * 3 + col / 3] & numBit) > 0) return false;
        return true;
    }

}

"""
