class TextCRDT:
    def __init__(self, site_id: str) -> None:
        self.site_id = site_id
        self.text = ""

    def to_string(self) -> str:
        return self.text
