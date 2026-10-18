"""Parse model table markup as data, never as executable HTML."""
from html.parser import HTMLParser


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cells, self.row, self.col, self.active, self.occupied = [], -1, 0, None, set()

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row += 1; self.col = 0
        elif tag in {"td", "th"} and self.row >= 0:
            while (self.row, self.col) in self.occupied:
                self.col += 1
            attrs = dict(attrs)
            rowspan = max(1, min(100, int(attrs.get("rowspan", 1))))
            colspan = max(1, min(100, int(attrs.get("colspan", 1))))
            self.active = dict(row=self.row, col=self.col, rowspan=rowspan, colspan=colspan, text="", status="requires_review")
            for row in range(self.row, self.row+rowspan):
                for col in range(self.col, self.col+colspan):
                    self.occupied.add((row,col))
            self.col += colspan
        elif tag == "br" and self.active is not None:
            self.active["text"] += "\n"

    def handle_data(self, data):
        if self.active is not None:
            self.active["text"] += data

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.active is not None:
            self.active["text"] = self.active["text"].strip() or None
            self.cells.append(self.active); self.active = None


def table_cells(text):
    if not text or "<table" not in text.lower():
        return None
    parser = TableParser()
    try:
        parser.feed(text)
    except (ValueError, TypeError):
        return None
    return parser.cells or None
