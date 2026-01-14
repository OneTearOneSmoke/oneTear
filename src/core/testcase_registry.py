import yaml
from pathlib import Path
from domain.testcase import TestCase

class TestCaseRegistry:
    def __init__(self):
        self._cases = []

    def load_dir(self, path):
        path = Path(path)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"TestCase path {path} 不存在或不是目录")
        for file in path.glob("*.yaml"):
            self.load_file(file)

    def load_file(self, path):
        with open(path) as f:
            data = yaml.safe_load(f)
        self._cases.append(TestCase.from_dict(data))

    def all(self):
        return self._cases
