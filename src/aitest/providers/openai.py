import json
import os
import urllib.request


class OpenAIProvider:
    """OpenAI-compatible provider；可指向 DeepSeek / vLLM / 其它兼容网关。"""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def complete(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is empty")
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            **kwargs,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=kwargs.get("timeout", 30)) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def embed(self, texts):
        # 保留最小实现；项目可替换为任意 embedding provider。
        return [[float(len(t))] for t in texts]
