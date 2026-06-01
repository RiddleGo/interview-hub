"""Python solution extracted from problems/前序/ACM模式如何构建二叉树.md."""
from __future__ import annotations

class TreeNode:
    def __init__(self, val = 0, left = None, right = None):
        self.val = val
        self.left = left
        self.right = right


# 根据数组构建二叉树

def construct_binary_tree(nums: []) -> TreeNode:
    if not nums: 
        return None
    # 用于存放构建好的节点
    root = TreeNode(-1)
    Tree = []
    # 将数组元素全部转化为树节点
    for i in range(len(nums)):
        if nums[i]!= -1:
            node = TreeNode(nums[i])
        else:
            node = None
        Tree.append(node)
        if i == 0:
            root = node
    # 直接判断2*i+2<len(Tree)会漏掉2*i+1=len(Tree)-1的情况
    for i in range(len(Tree)):
        if Tree[i] and 2 * i + 1 < len(Tree):
            Tree[i].left = Tree[2 * i + 1]
            if 2 * i + 2 < len(Tree):
                Tree[i].right = Tree[2 * i + 2]
    return root



# 算法:中序遍历二叉树

class Solution:
    def __init__(self):
        self.T = []
    def inorder(self, root: TreeNode) -> []:
        if not root:
            return 
        self.inorder(root.left)
        self.T.append(root.val)
        self.inorder(root.right)
        return self.T



# 验证创建二叉树的有效性,二叉排序树的中序遍历应为顺序排列

test_tree = [3, 1, 5, -1, 2, 4 ,6]
root = construct_binary_tree(test_tree)
A = Solution()
print(A.inorder(root))
