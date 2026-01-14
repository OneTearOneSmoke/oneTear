import itertools

class TestCase:
    def __init__(self, name, matrix, context, steps, hooks):
        """
        name:    测试用例名称
        matrix:  参数矩阵（用于参数化执行）
                 例如:
                 {
                   "pg_version": [14, 15],
                   "node_count": [1, 3]
                 }
        context: 基础上下文变量（所有 step / command / assert 都可引用）
        steps:   Step 列表，定义执行流程
        hooks:   Hooks(before / after / on_fail)
        """
        self.name = name
        self.matrix = matrix
        self.context = context
        self.steps = steps
        self.hooks = hooks

    def expand(self):
        """
        将 matrix 展开成多个具体的执行上下文（Execution Context）

        如果 matrix 为空:
            - 只执行一次，直接使用 context

        如果 matrix 非空:
            - 对 matrix 中所有参数做笛卡尔积
            - 每一种组合都会生成一个独立的 context
            - Engine 会对每一个 context 独立执行整个 TestCase
        """

        # 情况 1：没有 matrix，直接返回基础 context
        if not self.matrix:
            yield self.context
            return

        # matrix 的 key，如 ["pg_version", "node_count"]
        keys = self.matrix.keys()

        # itertools.product 生成所有参数组合（笛卡尔积）
        # 例如:
        # pg_version = [14, 15]
        # node_count = [1, 3]
        #
        # product 后得到:
        # (14, 1), (14, 3), (15, 1), (15, 3)
        for values in itertools.product(*self.matrix.values()):
            # 复制基础 context，避免污染原始 context
            ctx = dict(self.context)

            # 将参数组合写入 context
            # zip(keys, values) =>
            # {"pg_version": 14, "node_count": 1}
            ctx.update(dict(zip(keys, values)))

            # 产出一个完整可执行的 context
            yield ctx
