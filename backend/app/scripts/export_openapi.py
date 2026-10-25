import json

from app.config import ROOT_DIR
from app.main import app

OUTPUT = ROOT_DIR / "backend" / "openapi.json"

if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {OUTPUT}")
