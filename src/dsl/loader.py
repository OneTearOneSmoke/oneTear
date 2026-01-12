"""
DSL Loader
用于将 YAML 配置加载为 Command / Chaos / Testcase 对象
"""
import yaml, glob

def load_yaml(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_testcases(path="conf/testcases"):
    testcases = []
    for file in glob.glob(f"{path}/*.yaml"):
        testcases.append(load_yaml(file))
    return testcases

def load_commands(path="conf/commands.yaml"):
    return load_yaml(path)

def load_chaos(path="conf/chaos.yaml"):
    return load_yaml(path)



