"""Python solution extracted from problems/1382.将二叉搜索树变平衡.md."""
from __future__ import annotations

class Solution:
    def balanceBST(self, root: TreeNode) -> TreeNode:
        res = []
        # 有序树转成有序数组
        def traversal(cur: TreeNode):
            if not cur: return
            traversal(cur.left)
            res.append(cur.val)
            traversal(cur.right)
        # 有序数组转成平衡二叉树
        def getTree(nums: List, left, right):
            if left > right: return 
            mid = left + (right -left) // 2
            root = TreeNode(nums[mid])
            root.left = getTree(nums, left, mid - 1)
            root.right = getTree(nums, mid + 1, right)
            return root
        traversal(root)
        return getTree(res, 0, len(res) - 1)
