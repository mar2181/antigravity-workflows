# Gemini + Claude RAG Pipeline — Implementation Guide

> **Context:** Combines Google Gemini's embedding models (including multimodal) with Anthropic Claude for retrieval-augmented generation. Designed to integrate with the existing Antigravity Digital marketing automation system.
>
> **Created:** 2026-03-23
> **References:** Jack Roberts "AI Automations" course concepts, Google AI documentation, Anthropic API docs

---

## 1. Gemini Embedding Models — Complete Reference

Google offers two distinct embedding model families. Choosing the right one depends on whether you need text-only or multimodal (image/video) embeddings.

### A. Text Embedding Models (Gemini API — ai.google.dev)

| Model ID | Dimensions | Max Tokens | Task Types | Access |
|---|---|---|---|---|
| `text-embedding-004` | 768 (configurable: 256, 512, 768) | 2,048 | `RETRIEVAL_QUERY`, `RETRIEVAL_DOCUMENT`, `SEMANTIC_SIMILARITY`, `CLASSIFICATION`, `CLUSTERING` | Free tier via API key |
| `embedding-001` | 768 | 2,048 | Same as above | Legacy, use 004 instead |

**Key details for `text-embedding-004`:**
- Best general-purpose text embedding from Google as of early 2026
- Supports `task_type` parameter which optimizes the embedding for its intended use (always set this)
- Supports `title` parameter for document embeddings (improves retrieval quality)
- Configurable output dimensions (Matryoshka-style) — use 768 for max quality, 256 for cost/speed tradeoff
- Free tier: 1,500 requests/minute, no per-token cost
- Accessed via `generativelanguage.googleapis.com` (simple API key, no GCP project needed)

**API endpoint:**
```
POST https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key=YOUR_API_KEY
```

**Python (google-generativeai SDK):**
```python
import google.generativeai as genai

genai.configure(api_key="YOUR_GEMINI_API_KEY")

# Single text embedding
result = genai.embed_content(
    model="models/text-embedding-004",
    content="How to market a candy store on South Padre Island",
    task_type="RETRIEVAL_DOCUMENT",
    title="Marketing Strategy"  # optional, improves doc embeddings
)
embedding = result['embedding']  # list of 768 floats

# Batch embedding (up to 100 texts per call)
result = genai.embed_content(
    model="models/text-embedding-004",
    content=["text 1", "text 2", "text 3"],
    task_type="RETRIEVAL_DOCUMENT"
)
embeddings = result['embedding']  # list of lists
```

**Node.js (@google/generative-ai SDK):**
```javascript
import { GoogleGenerativeAI } from "@google/generative-ai";

const genAI = new GoogleGenerativeAI("YOUR_GEMINI_API_KEY");
const model = genAI.getGenerativeModel({ model: "text-embedding-004" });

// Single embedding
const result = await model.embedContent({
  content: { parts: [{ text: "your text here" }] },
  taskType: "RETRIEVAL_DOCUMENT",
  title: "Optional document title"
});
const embedding = result.embedding.values; // Float32Array of 768

// Batch embedding
const batchResult = await model.batchEmbedContents({
  requests: texts.map(text => ({
    content: { parts: [{ text }] },
    taskType: "RETRIEVAL_DOCUMENT"
  }))
});
const embeddings = batchResult.embeddings.map(e => e.values);
```

### B. Multimodal Embedding Model (Vertex AI — cloud.google.com)

| Model ID | Dimensions | Modalities | Access |
|---|---|---|---|
| `multimodalembedding@001` | 128, 256, 512, 1408 | Text + Image + Video | Vertex AI (requires GCP project + service account) |

**Critical distinction:** The multimodal model lives on **Vertex AI**, not the free Gemini API. It requires a GCP project, billing enabled, and authentication via service account or ADC (Application Default Credentials). It is NOT available via simple API key.

**What it can embed:**
- **Text:** Up to 32 tokens (short text only — this is NOT a replacement for text-embedding-004 for long documents)
- **Images:** JPEG, PNG, BMP, GIF — up to 20MB. Encodes visual features.
- **Video:** Up to 2 minutes. Extracts frames at configurable intervals and produces per-frame + aggregated embeddings.

**All modalities produce vectors in the SAME embedding space.** This is the key insight: you can embed a video frame and a text query, compute cosine similarity, and find which frames match the text. Cross-modal retrieval.

**Python (Vertex AI SDK):**
```python
from google.cloud import aiplatform
from vertexai.vision_models import MultiModalEmbeddingModel, Image, Video

aiplatform.init(project="your-gcp-project", location="us-central1")
model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding@001")

# Text embedding
text_emb = model.get_embeddings(
    contextual_text="candy store on the beach",
    dimension=1408  # 128, 256, 512, or 1408
)
text_vector = text_emb.text_embedding  # list of 1408 floats

# Image embedding
image = Image.load_from_file("storefront_photo.jpg")
img_emb = model.get_embeddings(
    image=image,
    dimension=1408
)
image_vector = img_emb.image_embedding

# Video embedding (extracts frames)
video = Video.load_from_file("store_walkthrough.mp4")
video_emb = model.get_embeddings(
    video=video,
    video_segment_config={"start_offset_sec": 0, "end_offset_sec": 60, "interval_sec": 10},
    dimension=1408
)
# Returns per-segment embeddings + timestamps
for segment in video_emb.video_embeddings:
    print(f"Time: {segment.start_offset_sec}s - {segment.end_offset_sec}s")
    print(f"Embedding: {len(segment.embedding)} dimensions")
```

**Cost (Vertex AI multimodal embeddings):**
- Text: $0.00025 per prediction
- Image: $0.001 per prediction
- Video: $0.002 per second of video

### C. Decision Matrix — Which Model to Use

| Use Case | Model | Why |
|---|---|---|
| Blog posts, ad copy, transcripts, competitor reports | `text-embedding-004` (Gemini API) | Free, 768d, handles long text, task-type optimization |
| YouTube thumbnails, ad images, storefront photos | `multimodalembedding@001` (Vertex AI) | Cross-modal search: "find images similar to this text" |
| Video frame search (find the moment someone says X) | `text-embedding-004` for transcript chunks | Cheaper + better for text; timestamp_url gives you the video link |
| Visual similarity (find competitor ads that look like ours) | `multimodalembedding@001` (Vertex AI) | Image-to-image similarity in shared embedding space |
| **Recommended default for Antigravity** | **text-embedding-004** | Free, no GCP needed, covers 90% of use cases |

---

## 2. Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONTENT INGESTION LAYER                          │
├──────────────┬──────────────┬─────────────┬────────────────────────┤
│ YouTube      │ Blog Posts   │ Ad Copy     │ Competitor Intel       │
│ yt-dlp +     │ blog_writer  │ ad_copy_    │ competitor_monitor     │
│ VTT parse    │ .py output   │ optimizer   │ .py + review_miner    │
│ + comments   │              │ .py output  │ .py output            │
└──────┬───────┴──────┬───────┴──────┬──────┴──────────┬─────────────┘
       │              │              │                 │
       ▼              ▼              ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CHUNKING + METADATA LAYER                        │
│                                                                     │
│  - Transcript chunks (500 words, 75 overlap) ← already built       │
│  - Blog sections (by H2 heading)                                    │
│  - Ad copy (full text per ad, small enough = 1 chunk)               │
│  - Competitor reports (by section: reviews, ads, GBP changes)       │
│  - Each chunk gets: source_type, client_key, timestamp, url         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EMBEDDING LAYER (Gemini)                         │
│                                                                     │
│  genai.embed_content(                                               │
│    model="models/text-embedding-004",                               │
│    content=chunk_text,                                              │
│    task_type="RETRIEVAL_DOCUMENT"                                   │
│  )                                                                  │
│                                                                     │
│  → 768-dimensional vector per chunk                                 │
│  → Batch: up to 100 texts per API call                              │
│  → Free tier: 1,500 req/min                                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VECTOR STORAGE LAYER                              │
│                                                                     │
│  Option A: Supabase pgvector (RECOMMENDED — already in stack)       │
│  Option B: ChromaDB (local, zero-config, good for dev)              │
│  Option C: Pinecone (managed, scales, costs money)                  │
│                                                                     │
│  Schema: id, embedding(768), text, metadata(jsonb)                  │
│          metadata = {source_type, client_key, url, timestamp, ...}  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RETRIEVAL LAYER                                   │
│                                                                     │
│  1. User query → embed with task_type="RETRIEVAL_QUERY"             │
│  2. Vector similarity search (cosine) → top K results               │
│  3. Optional: metadata filter (client_key, source_type, date)       │
│  4. Re-rank results (optional, using Cohere rerank or LLM)          │
│  5. Pack top N chunks into context window                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GENERATION LAYER (Claude)                        │
│                                                                     │
│  anthropic.messages.create(                                         │
│    model="claude-sonnet-4-20250514",                                │
│    system="You are a marketing strategist. Use ONLY the provided    │
│           context to answer. Cite sources with [Source: url].",      │
│    messages=[{                                                      │
│      "role": "user",                                                │
│      "content": f"Context:\n{retrieved_chunks}\n\nQuestion: {query}"│
│    }]                                                               │
│  )                                                                  │
│                                                                     │
│  Use cases:                                                         │
│  - "Write a blog post about X using our existing YouTube content"   │
│  - "What did competitors change in their GBP last week?"            │
│  - "Generate 5 ad angles based on our best-performing content"      │
│  - "Summarize everything we know about [topic] across all sources"  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Vector Database Comparison

### Option A: Supabase pgvector (RECOMMENDED)

**Why:** You already have Supabase in the HS Solutions project. pgvector is a PostgreSQL extension — it runs inside your existing Supabase instance.

```sql
-- Enable the extension (already in your schema!)
CREATE EXTENSION IF NOT EXISTS vector;

-- RAG chunks table
CREATE TABLE IF NOT EXISTS public.rag_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding VECTOR(768),  -- Gemini text-embedding-004 output
  metadata JSONB NOT NULL DEFAULT '{}',
  -- metadata contains: source_type, client_key, source_url,
  --   video_id, timestamp_url, chunk_index, created_at, title
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX ON public.rag_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Search function
CREATE OR REPLACE FUNCTION match_chunks(
  query_embedding VECTOR(768),
  match_count INT DEFAULT 10,
  filter_metadata JSONB DEFAULT '{}'
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    rc.id,
    rc.content,
    rc.metadata,
    1 - (rc.embedding <=> query_embedding) AS similarity
  FROM public.rag_chunks rc
  WHERE (filter_metadata = '{}' OR rc.metadata @> filter_metadata)
  ORDER BY rc.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
```

**Python client:**
```python
from supabase import create_client
import json

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Insert a chunk
supabase.table("rag_chunks").insert({
    "content": chunk_text,
    "embedding": embedding_vector,  # list of 768 floats
    "metadata": {
        "source_type": "youtube_transcript",
        "client_key": "sugar_shack",
        "video_id": "abc123",
        "timestamp_url": "https://youtube.com/watch?v=abc123&t=120s",
        "title": "Summer Marketing Ideas"
    }
}).execute()

# Search
results = supabase.rpc("match_chunks", {
    "query_embedding": query_vector,
    "match_count": 10,
    "filter_metadata": {"client_key": "sugar_shack"}
}).execute()
```

### Option B: ChromaDB (Local Development / Prototyping)

**Why:** Zero config, runs in-process, persists to disk. Perfect for rapid prototyping before committing to Supabase.

```python
import chromadb

client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(
    name="marketing_rag",
    metadata={"hnsw:space": "cosine"}
)

# Insert
collection.add(
    ids=["chunk_001"],
    embeddings=[embedding_vector],
    documents=["The chunk text content"],
    metadatas=[{"source_type": "youtube", "client_key": "sugar_shack"}]
)

# Search
results = collection.query(
    query_embeddings=[query_vector],
    n_results=10,
    where={"client_key": "sugar_shack"}
)
```

### Option C: Pinecone (Managed, Scalable)

Good if you outgrow Supabase. Free tier: 1 index, 100K vectors. Adds latency (network hop to managed service) but handles millions of vectors with zero ops.

### Recommendation

**Start with ChromaDB for prototyping** (zero cost, zero setup, works immediately).
**Move to Supabase pgvector for production** (you already have the infrastructure, and the pgvector extension is already enabled in your schema).
Skip Pinecone unless you hit >1M vectors (unlikely for 8 clients).

---

## 4. Required Packages

### Python (primary — matches existing Antigravity stack)

```bash
# Core embedding + generation
pip install google-generativeai      # Gemini API (text-embedding-004)
pip install anthropic                 # Claude API (generation)

# Vector storage (pick one)
pip install chromadb                  # Local vector DB (prototyping)
pip install supabase                  # Supabase client (production)

# Optional: Vertex AI multimodal embeddings (requires GCP)
pip install google-cloud-aiplatform   # Only if you need image/video embeddings

# Content processing (already in your stack)
# yt-dlp                             # YouTube transcripts (already installed)
# Pillow                             # Image handling
# numpy                              # Vector math
```

### Node.js (if building into Mission Control dashboard)

```bash
npm install @google/generative-ai     # Gemini API
npm install @anthropic-ai/sdk         # Claude API
npm install chromadb                   # ChromaDB client
npm install @supabase/supabase-js     # Supabase client
```

### Environment Variables Needed

```bash
# Add to gravity-claw/.env or a new .env in the RAG pipeline directory
GEMINI_API_KEY="your-gemini-api-key"          # Get from ai.google.dev
ANTHROPIC_API_KEY="your-anthropic-api-key"    # Already have via Claude Code
SUPABASE_URL="your-supabase-url"              # Already have for HS Solutions
SUPABASE_KEY="your-supabase-service-key"      # Already have

# Only if using Vertex AI multimodal:
GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
GCP_PROJECT_ID="your-gcp-project"
```

---

## 5. Integration Points with Existing Antigravity System

### A. YouTube Transcript Ingestion (Already Built — Just Add Embeddings)

The `youtube_scraper_skill.md` already has the full pipeline through Stage 3 (chunking). The missing step is embedding + storage.

```python
# Add after Stage 3 chunking in the YouTube pipeline
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def embed_and_store_chunks(chunks, client_key):
    """Embed transcript chunks and store in vector DB."""
    batch_size = 100  # Gemini allows up to 100 per batch call

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["text"] for c in batch]

        result = genai.embed_content(
            model="models/text-embedding-004",
            content=texts,
            task_type="RETRIEVAL_DOCUMENT"
        )

        for chunk, embedding in zip(batch, result["embedding"]):
            store_chunk(
                content=chunk["text"],
                embedding=embedding,
                metadata={
                    "source_type": "youtube_transcript",
                    "client_key": client_key,
                    "video_id": chunk["id"].split("_chunk_")[0],
                    "timestamp_url": chunk["timestamp_url"],
                    "title": chunk["title"],
                    "chunk_index": chunk["chunk_index"]
                }
            )
```

### B. Blog Writer Enhancement (blog_writer.py)

Currently generates blogs from keyword rankings. With RAG, it can pull from ALL existing content:

```python
def generate_blog_with_rag(client_key, keyword, topic):
    """Generate a blog post grounded in existing content."""

    # 1. Embed the query
    query_result = genai.embed_content(
        model="models/text-embedding-004",
        content=f"{keyword} {topic}",
        task_type="RETRIEVAL_QUERY"
    )

    # 2. Retrieve relevant chunks
    chunks = search_vectors(
        query_embedding=query_result["embedding"],
        filter={"client_key": client_key},
        top_k=15
    )

    # 3. Build context
    context = "\n\n---\n\n".join([
        f"[Source: {c['metadata']['source_type']} — {c['metadata'].get('title', 'untitled')}]\n"
        f"[URL: {c['metadata'].get('timestamp_url', c['metadata'].get('source_url', 'N/A'))}]\n"
        f"{c['content']}"
        for c in chunks
    ])

    # 4. Generate with Claude
    response = anthropic.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=(
            f"You are a content writer for {client_key}. "
            "Write a detailed, SEO-optimized blog post. "
            "Use ONLY the provided context as your source material. "
            "Include inline citations like [Source: title] when referencing specific information. "
            "Do not invent facts."
        ),
        messages=[{
            "role": "user",
            "content": f"Topic: {topic}\nTarget keyword: {keyword}\n\n"
                       f"Reference material:\n{context}\n\n"
                       f"Write a 1000-1500 word blog post."
        }]
    )

    return response.content[0].text
```

### C. Ad Copy Optimizer Enhancement (ad_copy_optimizer.py)

Pull winning angles from historical engagement data + competitor intel:

```python
def generate_ad_with_rag(client_key, angle, platform="facebook"):
    """Generate ad copy grounded in best-performing content + competitor analysis."""

    # Retrieve from multiple source types
    query = f"{angle} {platform} ad marketing"
    query_emb = embed_query(query)

    # Get our best content
    our_content = search_vectors(query_emb, {"client_key": client_key, "source_type": "youtube_transcript"}, top_k=5)

    # Get competitor insights
    competitor_intel = search_vectors(query_emb, {"client_key": client_key, "source_type": "competitor_report"}, top_k=5)

    # Get past ad performance
    past_ads = search_vectors(query_emb, {"client_key": client_key, "source_type": "ad_copy"}, top_k=5)

    # Combine and generate
    # ... (similar pattern to blog writer)
```

### D. Morning Brief Intelligence (morning_brief.py)

Index competitor reports and review data. Query across all clients:

```python
# After competitor_monitor.py runs nightly:
def ingest_competitor_report(report_path, client_key):
    """Chunk and embed a competitor report for RAG search."""
    report_text = Path(report_path).read_text()

    # Split by sections (## headers)
    sections = split_by_headers(report_text)

    for section in sections:
        embedding = embed_text(section["text"])
        store_chunk(
            content=section["text"],
            embedding=embedding,
            metadata={
                "source_type": "competitor_report",
                "client_key": client_key,
                "section": section["header"],
                "report_date": datetime.now().isoformat(),
                "source_url": report_path
            }
        )
```

---

## 6. Complete Working Script — RAG Pipeline MVP

Save as `C:/Users/mario/.gemini/antigravity/tools/execution/rag_pipeline.py`:

```python
#!/usr/bin/env python3
"""
Gemini + Claude RAG Pipeline MVP
Embed content with Gemini text-embedding-004, store in ChromaDB, retrieve + generate with Claude.

Usage:
    # Ingest content
    python rag_pipeline.py ingest --client sugar_shack --source youtube --path ./data/transcripts/
    python rag_pipeline.py ingest --client sugar_shack --source blog --path ./blogs/
    python rag_pipeline.py ingest --client sugar_shack --source competitor --path ./competitor_reports/

    # Query
    python rag_pipeline.py query --client sugar_shack --question "What are our best summer marketing angles?"
    python rag_pipeline.py query --client all --question "Which competitors are running beach rental promotions?"

    # Generate blog from RAG context
    python rag_pipeline.py blog --client sugar_shack --keyword "candy store south padre" --topic "Summer vacation treats"
"""

import os
import sys
import json
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# ─── Dependencies ────────────────────────────────────────────────────────────

try:
    import google.generativeai as genai
except ImportError:
    print("Run: pip install google-generativeai")
    sys.exit(1)

try:
    import chromadb
except ImportError:
    print("Run: pip install chromadb")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("Run: pip install anthropic")
    sys.exit(1)

# ─── Configuration ───────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR.parent.parent / "scratch" / "gravity-claw" / ".env"
CHROMA_DIR = SCRIPT_DIR / "rag_data" / "chroma"
EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIM = 768
GENERATION_MODEL = "claude-sonnet-4-20250514"  # or claude-opus-4-20250514 for complex tasks
CHUNK_SIZE = 500       # words
CHUNK_OVERLAP = 75     # words


def load_env():
    """Load environment variables from .env file."""
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")

    # Set from env file or existing environment
    for key in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY"]:
        val = env.get(key, os.environ.get(key))
        if val:
            os.environ[key] = val

    return env


def init_gemini():
    """Initialize Gemini API."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set. Get one from https://ai.google.dev/")
        sys.exit(1)
    genai.configure(api_key=api_key)


def init_chroma():
    """Initialize ChromaDB with persistent storage."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name="antigravity_rag",
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def init_claude():
    """Initialize Anthropic client."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


# ─── Embedding Functions ────────────────────────────────────────────────────

def embed_texts(texts: List[str], task_type: str = "RETRIEVAL_DOCUMENT") -> List[List[float]]:
    """Embed a list of texts using Gemini text-embedding-004."""
    all_embeddings = []
    batch_size = 100  # Gemini max per call

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=batch,
            task_type=task_type
        )
        all_embeddings.extend(result["embedding"])

    return all_embeddings


def embed_query(query: str) -> List[float]:
    """Embed a search query."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=query,
        task_type="RETRIEVAL_QUERY"
    )
    return result["embedding"]


# ─── Chunking Functions ─────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    stride = chunk_size - overlap
    chunks = []

    for i in range(0, len(words), stride):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.split()) >= overlap:  # skip tiny trailing chunks
            chunks.append(chunk)

    return chunks


def chunk_markdown_by_headers(text: str) -> List[Dict]:
    """Split markdown by H2 headers, keeping header as metadata."""
    sections = []
    current_header = "Introduction"
    current_lines = []

    for line in text.split("\n"):
        if line.startswith("## "):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append({"header": current_header, "text": body})
            current_header = line.lstrip("# ").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append({"header": current_header, "text": body})

    return sections


# ─── Ingestion Functions ────────────────────────────────────────────────────

def ingest_file(collection, filepath: Path, client_key: str, source_type: str):
    """Ingest a single file into the vector store."""
    text = filepath.read_text(encoding="utf-8", errors="ignore")

    if source_type in ["blog", "competitor"]:
        # Split by headers for structured documents
        sections = chunk_markdown_by_headers(text)
        for section in sections:
            sub_chunks = chunk_text(section["text"])
            for idx, chunk in enumerate(sub_chunks):
                chunk_id = hashlib.md5(f"{filepath}:{section['header']}:{idx}".encode()).hexdigest()
                embeddings = embed_texts([chunk])

                collection.upsert(
                    ids=[chunk_id],
                    embeddings=embeddings,
                    documents=[chunk],
                    metadatas=[{
                        "source_type": source_type,
                        "client_key": client_key,
                        "source_file": str(filepath),
                        "section": section["header"],
                        "chunk_index": idx,
                        "ingested_at": datetime.now().isoformat()
                    }]
                )
    else:
        # Plain text chunking (transcripts, ad copy, etc.)
        chunks = chunk_text(text)
        for idx, chunk in enumerate(chunks):
            chunk_id = hashlib.md5(f"{filepath}:{idx}".encode()).hexdigest()
            embeddings = embed_texts([chunk])

            collection.upsert(
                ids=[chunk_id],
                embeddings=embeddings,
                documents=[chunk],
                metadatas=[{
                    "source_type": source_type,
                    "client_key": client_key,
                    "source_file": str(filepath),
                    "chunk_index": idx,
                    "ingested_at": datetime.now().isoformat()
                }]
            )

    print(f"  Ingested: {filepath.name}")


def ingest_directory(collection, dir_path: Path, client_key: str, source_type: str):
    """Ingest all text/markdown files from a directory."""
    extensions = {".md", ".txt", ".vtt", ".json"}
    files = [f for f in dir_path.rglob("*") if f.suffix in extensions and f.is_file()]

    print(f"Found {len(files)} files to ingest from {dir_path}")
    for f in sorted(files):
        ingest_file(collection, f, client_key, source_type)

    print(f"Ingestion complete. Collection now has {collection.count()} chunks.")


# ─── Retrieval Functions ────────────────────────────────────────────────────

def search(collection, query: str, client_key: Optional[str] = None,
           source_type: Optional[str] = None, top_k: int = 10) -> List[Dict]:
    """Search the vector store."""
    query_embedding = embed_query(query)

    where_filter = {}
    if client_key and client_key != "all":
        where_filter["client_key"] = client_key
    if source_type:
        where_filter["source_type"] = source_type

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter if where_filter else None,
        include=["documents", "metadatas", "distances"]
    )

    output = []
    for i in range(len(results["ids"][0])):
        output.append({
            "id": results["ids"][0][i],
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "similarity": 1 - results["distances"][0][i]  # cosine distance to similarity
        })

    return output


# ─── Generation Functions ───────────────────────────────────────────────────

def generate_answer(claude_client, query: str, chunks: List[Dict],
                    client_key: str, output_type: str = "answer") -> str:
    """Generate a response using Claude with retrieved context."""

    # Build context from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        source_label = f"{meta.get('source_type', 'unknown')} — {meta.get('section', meta.get('source_file', 'N/A'))}"
        context_parts.append(
            f"[Source {i+1}: {source_label}]\n"
            f"[Similarity: {chunk['similarity']:.3f}]\n"
            f"{chunk['content']}"
        )

    context = "\n\n---\n\n".join(context_parts)

    system_prompts = {
        "answer": (
            f"You are a marketing intelligence assistant for Antigravity Digital, "
            f"currently focused on client: {client_key}. "
            "Answer the question using ONLY the provided reference material. "
            "Cite sources using [Source N] notation. "
            "If the context does not contain enough information, say so explicitly."
        ),
        "blog": (
            f"You are an SEO content writer for {client_key}. "
            "Write a detailed, engaging blog post using the provided reference material as your source. "
            "Include inline citations. Target 1000-1500 words. "
            "Use H2 and H3 headers for structure. Include a meta description at the top."
        ),
        "ad_copy": (
            f"You are a Facebook ad copywriter for {client_key}. "
            "Write compelling ad copy using insights from the provided context. "
            "Keep copy under 300 words. Maximum 3 hashtags. "
            "Include a clear call-to-action."
        )
    }

    response = claude_client.messages.create(
        model=GENERATION_MODEL,
        max_tokens=4096,
        system=system_prompts.get(output_type, system_prompts["answer"]),
        messages=[{
            "role": "user",
            "content": f"Reference material:\n\n{context}\n\n---\n\nRequest: {query}"
        }]
    )

    return response.content[0].text


# ─── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Gemini + Claude RAG Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest content into vector store")
    ingest_parser.add_argument("--client", required=True, help="Client key (sugar_shack, island_arcade, etc.)")
    ingest_parser.add_argument("--source", required=True, choices=["youtube", "blog", "competitor", "ad_copy", "general"])
    ingest_parser.add_argument("--path", required=True, help="File or directory to ingest")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query the knowledge base")
    query_parser.add_argument("--client", default="all", help="Client key or 'all'")
    query_parser.add_argument("--question", required=True, help="Your question")
    query_parser.add_argument("--source", default=None, help="Filter by source type")
    query_parser.add_argument("--top-k", type=int, default=10, help="Number of results")
    query_parser.add_argument("--raw", action="store_true", help="Show raw chunks without Claude generation")

    # Blog command
    blog_parser = subparsers.add_parser("blog", help="Generate a RAG-grounded blog post")
    blog_parser.add_argument("--client", required=True)
    blog_parser.add_argument("--keyword", required=True)
    blog_parser.add_argument("--topic", required=True)

    # Stats command
    subparsers.add_parser("stats", help="Show vector store statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize
    env = load_env()
    init_gemini()
    collection = init_chroma()

    if args.command == "ingest":
        path = Path(args.path)
        if path.is_dir():
            ingest_directory(collection, path, args.client, args.source)
        elif path.is_file():
            ingest_file(collection, path, args.client, args.source)
        else:
            print(f"ERROR: Path not found: {path}")
            sys.exit(1)

    elif args.command == "query":
        results = search(collection, args.question, args.client, args.source, args.top_k)

        if not results:
            print("No results found.")
            return

        if args.raw:
            for r in results:
                print(f"\n--- [Similarity: {r['similarity']:.3f}] ---")
                print(f"Source: {r['metadata'].get('source_type')} | {r['metadata'].get('source_file', 'N/A')}")
                print(r["content"][:500])
        else:
            claude_client = init_claude()
            answer = generate_answer(claude_client, args.question, results, args.client)
            print("\n" + answer)

    elif args.command == "blog":
        query = f"{args.keyword} {args.topic}"
        results = search(collection, query, args.client, top_k=15)

        if not results:
            print("No context found. Ingest content first.")
            return

        claude_client = init_claude()
        blog = generate_answer(
            claude_client,
            f"Write a blog post about '{args.topic}' targeting the keyword '{args.keyword}'.",
            results,
            args.client,
            output_type="blog"
        )

        # Save output
        out_dir = SCRIPT_DIR / "rag_output" / args.client
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = args.keyword.replace(" ", "_")[:50]
        out_path = out_dir / f"blog_{slug}_{datetime.now().strftime('%Y%m%d')}.md"
        out_path.write_text(blog, encoding="utf-8")
        print(f"\nBlog saved to: {out_path}")
        print(f"\n{blog[:500]}...")

    elif args.command == "stats":
        count = collection.count()
        print(f"Total chunks in vector store: {count}")

        if count > 0:
            # Sample to show metadata distribution
            sample = collection.peek(limit=min(count, 100))
            source_types = {}
            client_keys = {}
            for meta in sample["metadatas"]:
                st = meta.get("source_type", "unknown")
                ck = meta.get("client_key", "unknown")
                source_types[st] = source_types.get(st, 0) + 1
                client_keys[ck] = client_keys.get(ck, 0) + 1

            print(f"\nSource types (sample): {json.dumps(source_types, indent=2)}")
            print(f"Client keys (sample): {json.dumps(client_keys, indent=2)}")


if __name__ == "__main__":
    main()
```

---

## 7. Getting Started — Step by Step

### Step 1: Get a Gemini API Key (Free)

1. Go to https://ai.google.dev/
2. Click "Get API Key" (or https://aistudio.google.com/apikey)
3. Create key — no billing needed, free tier is generous
4. Add to `.env`: `GEMINI_API_KEY="your-key-here"`

### Step 2: Install Dependencies

```bash
cd "C:/Users/mario/.gemini/antigravity/tools/execution"
pip install google-generativeai chromadb anthropic
```

### Step 3: Test the Pipeline

```bash
# Ingest a competitor report
python rag_pipeline.py ingest \
  --client sugar_shack \
  --source competitor \
  --path ./competitor_reports/

# Query it
python rag_pipeline.py query \
  --client sugar_shack \
  --question "What promotions are our competitors running?"

# Check stats
python rag_pipeline.py stats
```

### Step 4: Ingest YouTube Transcripts

Once you have VTT files from the YouTube scraper pipeline:

```bash
python rag_pipeline.py ingest \
  --client sugar_shack \
  --source youtube \
  --path ./data/vtt/
```

### Step 5: Generate RAG-Grounded Content

```bash
python rag_pipeline.py blog \
  --client sugar_shack \
  --keyword "candy store south padre island" \
  --topic "Best candy shops for family vacation"
```

---

## 8. Migration to Supabase pgvector (Production)

When ready to move from ChromaDB to Supabase:

1. Run the SQL from Section 3A to create the `rag_chunks` table
2. Replace the ChromaDB calls with Supabase RPC calls
3. The embedding logic (Gemini API calls) stays identical
4. The retrieval logic uses the `match_chunks` SQL function instead of ChromaDB query

The script is designed so that swapping the storage backend requires changing only `init_chroma()`, `ingest_file()`, and `search()` — the embedding and generation layers are storage-agnostic.

---

## 9. Advanced: Multimodal RAG (Phase 2)

If you later need to search across images (e.g., "find all ad images that look like a beach sunset"):

1. Set up a GCP project with Vertex AI enabled
2. `pip install google-cloud-aiplatform`
3. Use `multimodalembedding@001` to embed images alongside text
4. Store in a SEPARATE collection (different dimension: 1408 vs 768)
5. Cross-modal queries: embed text query with multimodal model, search against image embeddings

This is Phase 2 — the text-only pipeline covers 90% of the immediate use cases.

---

## 10. Jack Roberts Course Context

The "AI Automations" course on Skool teaches this pattern as part of the "Second Brain" concept:

1. **Ingest everything** — YouTube transcripts, meeting notes, competitor data, client briefs
2. **Embed with Gemini** — free, fast, high quality for text
3. **Store in vectors** — any DB that supports cosine similarity
4. **Retrieve contextually** — semantic search beats keyword search
5. **Generate with the best LLM** — Claude for nuanced, brand-safe marketing copy

The key insight: **Use the best tool for each job.** Gemini's embeddings are free and excellent for vectorization. Claude is superior for long-form generation with brand voice adherence. Combining them gives you a pipeline that is both cost-effective and high-quality.

The `text-embedding-004` model from Gemini is the workhorse. The multimodal model (`multimodalembedding@001`) on Vertex AI is the power move for when you need cross-modal search (text-to-image, image-to-image). Start with text-only and expand.
