from pathlib import Path
import json

def load(root):
    return json.loads((Path(root)/"translation/names.ko.json").read_text(encoding="utf8"))
