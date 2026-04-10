"""Build SQLite FTS5 full-text index over all documents.

Usage: python -m scripts.build_fts_index
"""

from app.services.keyword_search import build_index

if __name__ == "__main__":
    print("Building FTS5 keyword search index...")
    count = build_index()
    print(f"Done. {count:,} documents indexed.")
