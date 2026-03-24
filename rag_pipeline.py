#!/usr/bin/env python3
"""
rag_pipeline.py — Knowledge Base RAG Pipeline

Indexes all marketing content (blog posts, ad copy, competitor intel, morning briefs)
into Pinecone for semantic search. Query from CLI or Telegram.

Uses: OpenAI text-embedding-3-small for embeddings, Pinecone for vector storage.

Usage:
    # Index all content
    python rag_pipeline.py index

    # Index specific content type
    python rag_pipeline.py index --type blogs
    python rag_pipeline.py index --type competitor
    python rag_pipeline.py index --type ads
    python rag_pipeline.py index --type briefs

    # Search
    python rag_pipeline.py search "what ad angles work for sugar shack"
    python rag_pipeline.py search "competitor weaknesses island arcade" --top 5

    # Stats
    python rag_pipeline.py stats
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

EXECUTION_DIR = Path(__file__).resolve().parent
ENV_FILE = EXECUTION_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"

PINECONE_INDEX_NAME = "antigravity-knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # local model, free, no API needed
EMBEDDING_DIMS = 384  # all-MiniLM-L6-v2 output dimensions

# Content directories to index
CONTENT_DIRS = {
    "blogs": EXECUTION_DIR / "blog_posts",
    "competitor": EXECUTION_DIR / "competitor_reports",
    "briefs": EXECUTION_DIR / "morning_briefs",
    "ads": EXECUTION_DIR,  # will filter for *_ADS_FINAL.md
    "programs": EXECUTION_DIR,  # client program.md files
}

VALID_CLIENTS = [
    "sugar_shack", "island_arcade", "island_candy", "juan",
    "spi_fun_rentals", "custom_designs_tx", "optimum_clinic", "optimum_foundation",
]


def load_env():
    env = {}
    try:
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


ENV = load_env()
OPENROUTER_API_KEY = (os.environ.get("OPENROUTER_API_KEY") or ENV.get("OPENROUTER_API_KEY", "")).strip()
OPENAI_API_KEY = (os.environ.get("OPENAI_API_KEY") or ENV.get("OPENAI_API_KEY", "")).strip()
PINECONE_API_KEY = (os.environ.get("PINECONE_API_KEY") or ENV.get("PINECONE_API_KEY", "")).strip()


# ─── EMBEDDING ───────────────────────────────────────────────────────────────

_model_cache = None

def _get_model():
    """Lazy-load the sentence-transformers model (cached)."""
    global _model_cache
    if _model_cache is None:
        from sentence_transformers import SentenceTransformer
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings locally via sentence-transformers. Free, no API needed."""
    model = _get_model()
    # Clean texts — remove empty and truncate long ones
    cleaned = [t[:8000] if t else "empty" for t in texts]
    embeddings = model.encode(cleaned, show_progress_bar=len(cleaned) > 10)
    return [e.tolist() for e in embeddings]


def get_single_embedding(text: str) -> list[float]:
    return get_embeddings([text])[0]


# ─── PINECONE ────────────────────────────────────────────────────────────────

def get_pinecone_index():
    """Get or create the Pinecone index."""
    from pinecone import Pinecone, ServerlessSpec

    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Check if index exists
    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        print(f"  Creating Pinecone index '{PINECONE_INDEX_NAME}'...")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMS,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for index to be ready
        while not pc.describe_index(PINECONE_INDEX_NAME).status.ready:
            time.sleep(2)
        print(f"  ✅ Index created")

    return pc.Index(PINECONE_INDEX_NAME)


# ─── CONTENT COLLECTORS ──────────────────────────────────────────────────────

def collect_blogs() -> list[dict]:
    """Collect blog posts from all clients."""
    docs = []
    blog_dir = CONTENT_DIRS["blogs"]
    if not blog_dir.exists():
        return docs

    for client_dir in blog_dir.iterdir():
        if not client_dir.is_dir():
            continue
        client = client_dir.name
        for md_file in client_dir.glob("*_meta.json"):
            try:
                meta = json.loads(md_file.read_text(encoding="utf-8"))
                # Find the corresponding markdown
                base = md_file.stem.replace("_meta", "")
                md_path = client_dir / f"{base}.md"
                if md_path.exists():
                    content = md_path.read_text(encoding="utf-8", errors="replace")[:10000]
                    docs.append({
                        "id": f"blog_{client}_{base}",
                        "text": content,
                        "metadata": {
                            "type": "blog",
                            "client": client,
                            "keyword": meta.get("keyword", ""),
                            "date": base[:10],
                            "source": str(md_path),
                        }
                    })
            except Exception:
                continue
    return docs


def collect_competitor_reports() -> list[dict]:
    """Collect competitor intelligence reports."""
    docs = []
    report_dir = CONTENT_DIRS["competitor"]
    if not report_dir.exists():
        return docs

    for f in report_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")[:10000]
            docs.append({
                "id": f"competitor_{f.stem}",
                "text": content,
                "metadata": {
                    "type": "competitor_intel",
                    "date": f.stem[:10] if f.stem[:4].isdigit() else "",
                    "source": str(f),
                }
            })
        except Exception:
            continue
    return docs


def collect_morning_briefs() -> list[dict]:
    """Collect morning brief reports."""
    docs = []
    brief_dir = CONTENT_DIRS["briefs"]
    if not brief_dir.exists():
        return docs

    for f in brief_dir.glob("*.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="replace")[:10000]
            docs.append({
                "id": f"brief_{f.stem}",
                "text": content,
                "metadata": {
                    "type": "morning_brief",
                    "date": f.stem[:10] if f.stem[:4].isdigit() else "",
                    "source": str(f),
                }
            })
        except Exception:
            continue
    return docs


def collect_ads() -> list[dict]:
    """Collect ad campaign final documents."""
    docs = []
    # Check execution dir and skills dir for *_ADS_FINAL.md
    for pattern_dir in [EXECUTION_DIR, EXECUTION_DIR.parent.parent / "scratch" / "skills"]:
        if not pattern_dir.exists():
            continue
        for f in pattern_dir.rglob("*ADS_FINAL*.md"):
            try:
                content = f.read_text(encoding="utf-8", errors="replace")[:10000]
                # Extract client name from path
                client = "unknown"
                for c in VALID_CLIENTS:
                    if c in str(f).lower().replace("-", "_"):
                        client = c
                        break
                docs.append({
                    "id": f"ads_{f.stem}_{hashlib.md5(str(f).encode()).hexdigest()[:8]}",
                    "text": content,
                    "metadata": {
                        "type": "ad_campaign",
                        "client": client,
                        "source": str(f),
                    }
                })
            except Exception:
                continue
    return docs


def collect_programs() -> list[dict]:
    """Collect client program.md steering documents."""
    docs = []
    for client in VALID_CLIENTS:
        program_path = EXECUTION_DIR / client / "program.md"
        if program_path.exists():
            try:
                content = program_path.read_text(encoding="utf-8", errors="replace")[:10000]
                docs.append({
                    "id": f"program_{client}",
                    "text": content,
                    "metadata": {
                        "type": "program",
                        "client": client,
                        "source": str(program_path),
                    }
                })
            except Exception:
                continue
    return docs


COLLECTORS = {
    "blogs": collect_blogs,
    "competitor": collect_competitor_reports,
    "briefs": collect_morning_briefs,
    "ads": collect_ads,
    "programs": collect_programs,
}


# ─── COMMANDS ────────────────────────────────────────────────────────────────

def cmd_index(args):
    """Index content into Pinecone."""
    print("\n📚 RAG Pipeline — Indexing Content\n")

    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not found"); sys.exit(1)

    # Collect documents
    all_docs = []
    types_to_index = [args.type] if args.type else list(COLLECTORS.keys())

    for content_type in types_to_index:
        if content_type not in COLLECTORS:
            print(f"  ⚠️ Unknown type: {content_type}")
            continue
        print(f"  📁 Collecting {content_type}...")
        docs = COLLECTORS[content_type]()
        print(f"     Found {len(docs)} documents")
        all_docs.extend(docs)

    if not all_docs:
        print("\n  No documents found to index.")
        return

    print(f"\n  Total: {len(all_docs)} documents")

    # Generate embeddings
    print(f"  🧮 Generating embeddings ({EMBEDDING_MODEL})...")
    texts = [d["text"] for d in all_docs]
    embeddings = get_embeddings(texts)
    print(f"  ✅ {len(embeddings)} embeddings generated")

    # Upsert to Pinecone
    print(f"  📌 Upserting to Pinecone ({PINECONE_INDEX_NAME})...")
    index = get_pinecone_index()

    vectors = []
    for doc, emb in zip(all_docs, embeddings):
        vectors.append({
            "id": doc["id"],
            "values": emb,
            "metadata": {
                **doc["metadata"],
                "text_preview": doc["text"][:500],
            }
        })

    # Batch upsert (100 at a time)
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)
        print(f"     Upserted {min(i + batch_size, len(vectors))}/{len(vectors)}")

    print(f"\n✅ Indexed {len(vectors)} documents into Pinecone")
    print(f"   Embedding cost: $0.00 (local model)")


def cmd_search(args):
    """Search the knowledge base."""
    query = args.query
    top_k = args.top

    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not found"); sys.exit(1)

    print(f"\n🔍 Searching: \"{query}\" (top {top_k})\n")

    # Embed the query
    query_embedding = get_single_embedding(query)

    # Search Pinecone
    index = get_pinecone_index()

    # Build filter if client specified
    filter_dict = {}
    if args.client:
        filter_dict["client"] = args.client
    if args.type:
        filter_dict["type"] = args.type

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict if filter_dict else None,
    )

    if not results.matches:
        print("  No results found.")
        return

    for i, match in enumerate(results.matches, 1):
        meta = match.metadata or {}
        score = match.score
        print(f"  [{i}] Score: {score:.4f} | Type: {meta.get('type', '?')} | Client: {meta.get('client', 'n/a')}")
        if meta.get("date"):
            print(f"      Date: {meta['date']}")
        preview = meta.get("text_preview", "")[:200]
        print(f"      {preview}...")
        print()

    # If --context flag, also output combined context for LLM use
    if args.context:
        context = "\n\n---\n\n".join(
            m.metadata.get("text_preview", "") for m in results.matches
        )
        print(f"\n{'='*60}")
        print("COMBINED CONTEXT (for LLM):")
        print(f"{'='*60}\n")
        print(context)


def cmd_stats(args):
    """Show index statistics."""
    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not found"); sys.exit(1)

    print(f"\n📊 RAG Pipeline Stats\n")

    index = get_pinecone_index()
    stats = index.describe_index_stats()

    print(f"  Index: {PINECONE_INDEX_NAME}")
    print(f"  Total vectors: {stats.total_vector_count}")
    print(f"  Dimension: {stats.dimension}")

    if stats.namespaces:
        print(f"  Namespaces:")
        for ns, ns_stats in stats.namespaces.items():
            print(f"    {ns or '(default)'}: {ns_stats.vector_count} vectors")


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RAG Knowledge Base Pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Index command
    idx_parser = subparsers.add_parser("index", help="Index content into Pinecone")
    idx_parser.add_argument("--type", choices=list(COLLECTORS.keys()),
                            help="Index specific content type only")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search the knowledge base")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--top", type=int, default=3, help="Number of results (default: 3)")
    search_parser.add_argument("--client", help="Filter by client name")
    search_parser.add_argument("--type", help="Filter by content type")
    search_parser.add_argument("--context", action="store_true",
                               help="Output combined context for LLM use")

    # Stats command
    subparsers.add_parser("stats", help="Show index statistics")

    args = parser.parse_args()

    if args.command == "index":
        cmd_index(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "stats":
        cmd_stats(args)


if __name__ == "__main__":
    main()
