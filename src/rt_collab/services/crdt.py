class TextCRDT:
    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self.text = ""
        self._ops: list[dict] = []

    def to_string(self) -> str:
        return self.text

    def local_insert(self, index: int, text: str) -> dict:
        before = self.text[:index]
        after = self.text[index:]
        self.text = before + text + after
        op = {"type": "insert", "index": index, "text": text}
        self._ops.append(op)
        return op
