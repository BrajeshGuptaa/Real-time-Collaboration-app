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

    def local_delete(self, index: int, length: int) -> dict:
        before = self.text[:index]
        removed = self.text[index:index + length]
        after = self.text[index + length:]
        self.text = before + after
        op = {"type": "delete", "index": index, "length": length, "removed": removed}
        self._ops.append(op)
        return op

    def apply(self, op: dict) -> None:
        t = op.get("type")
        if t == "insert":
            self.local_insert(int(op["index"]), str(op["text"]))
        elif t == "delete":
            self.local_delete(int(op["index"]), int(op["length"]))
