"""Print a fallo with numbered paragraphs, for gold labeling: python -m spikes.jev_fase1.show <id> [<id> ...]"""

import sqlite3
import sys

from scripts.config import settings
from scripts.labeling.state import build_state

db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
for doc_id in sys.argv[1:]:
    doc = dict(db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone())
    state = build_state(doc)
    print(f"===== {doc_id} | {doc['caratula']} | {doc['tribunal']} | {doc['fecha']} | objeto: {doc['objeto']}")
    for pid, text in state["parrafos"].items():
        print(f"[{pid}] {text}")
    print()
