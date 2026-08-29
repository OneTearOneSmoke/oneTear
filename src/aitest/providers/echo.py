class EchoProvider:
    name = "echo"

    def complete(self, prompt: str, **kwargs) -> str:
        text = prompt[:200] + ("..." if len(prompt) > 200 else "")
        return f"[echo] {text}"

    def embed(self, texts):
        return [[float(len(t))] for t in texts]
