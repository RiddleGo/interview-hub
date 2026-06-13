"""Python solution extracted from problems/0701.二叉搜索树中的插入操作.md."""
from __future__ import annotations

class Solution:
    def __init__(self):
        self.parent = None

    def traversal(self, cur, val):
        if cur is None:
            node = TreeNode(val)
            if val > self.parent.val:
                self.parent.right = node
            else:
                self.parent.left = node
            return

        self.parent = cur
        if cur.val > val:
            self.traversal(cur.left, val)
        if cur.val < val:
            self.traversal(cur.right, val)

    def insertIntoBST(self, root, val):
        self.parent = TreeNode(0)
        if root is None:
            return TreeNode(val)
        self.traversal(root, val)
        return root
