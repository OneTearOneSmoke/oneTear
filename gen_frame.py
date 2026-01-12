#!/usr/bin/env python3
import os

# 框架根目录
ROOT_DIR = "auto_test_framework"

# 目录结构
DIRS = [
    "core",
    "command",
    "chaos",
    "dsl",
    "assertor",
    "observability",
    "cases",
    "conf",
]

# 基础文件模板
FILES = {
    "core/engine.py": "# 执行引擎骨架\n",
    "core/context.py": "# 上下文定义\n",
    "core/result.py": "# 结果对象\n",
    "command/base.py": "# Command 抽象\n",
    "command/shell.py": "# ShellCommand 实现\n",
    "chaos/base.py": "# Chaos 抽象\n",
    "chaos/process.py": "# 进程相关故障\n",
    "chaos/network.py": "# 网络相关故障\n",
    "dsl/loader.py": "# DSL YAML Loader\n",
    "assertor/base.py": "# 断言抽象\n",
    "assertor/contains.py": "# contains 断言\n",
    "assertor/eventually.py": "# eventually 断言\n",
    "observability/otel.py": "# OpenTelemetry 初始化\n",
    "observability/allure.py": "# Allure 集成\n",
    "cases/__init__.py": "",
    "conf/commands.yaml": "# 原子命令配置\n",
    "conf/chaos.yaml": "# 原子故障配置\n",
    "conf/testcases.yaml": "# 测试用例组合配置\n",
    "pytest.ini": "[pytest]\naddopts = -v --tb=short\n",
    "pyproject.toml": "[project]\nname = 'auto_test_framework'\n",
}

def mkdirs(root, dirs):
    for d in dirs:
        path = os.path.join(root, d)
        os.makedirs(path, exist_ok=True)
        print(f"Created dir: {path}")

def create_files(root, files):
    for path, content in files.items():
        full_path = os.path.join(root, path)
        dir_path = os.path.dirname(full_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created file: {full_path}")

if __name__ == "__main__":
    mkdirs(ROOT_DIR, DIRS)
    create_files(ROOT_DIR, FILES)
    print(f"\n✅ 自动化测试框架目录结构已生成在 {ROOT_DIR} 下")
