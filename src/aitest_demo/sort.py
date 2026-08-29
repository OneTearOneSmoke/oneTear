"""一些给 AI 测试框架验证用的示例算法实现。"""


def bubble(xs):
    a = list(xs)
    n = len(a)
    for i in range(n):
        for j in range(n - 1 - i):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
    return a


def quick(xs):
    a = list(xs)
    if len(a) <= 1:
        return a
    p = a[0]
    left = [x for x in a[1:] if x < p]
    right = [x for x in a[1:] if x >= p]
    return quick(left) + [p] + quick(right)


def buggy_sort(xs):
    """故意写错，用例里要能抓到。"""
    return sorted(set(xs))  # 丢重复元素
