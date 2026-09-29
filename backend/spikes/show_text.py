"""Print ONLY the ruling's text, numbered by paragraph (blind review: no stored metadata shown).

Usage: python -m spikes.show_text <id> [<id> ...]
"""

import sqlite3
import sys

from scripts import quality
from scripts.config import settings

db = sqlite3.connect(f"file:{settings.data_root / 'catalog.db'}?mode=ro", uri=True)
for doc_id in sys.argv[1:]:
    texto = db.execute("SELECT texto FROM documents WHERE id=?", (doc_id,)).fetchone()[0]
    print(f"===== fallo {doc_id}")
    for i, p in enumerate(quality.split_paragraphs(texto)):
        print(f"[p{i}] {p}")
    print()
