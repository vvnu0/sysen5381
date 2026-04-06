# rag_guardian.py
# Semantic RAG with Guardian API Articles
# Pairs with app.py (Guardian News Coverage Analyzer)
# Tim Fraser / Nairv

# This script demonstrates Retrieval-Augmented Generation (RAG) using
# Guardian newspaper articles. It fetches articles via the Guardian API,
# embeds their summaries with sentence-transformers, stores them in a
# SQLite vector database (sqlite-vec), and lets you ask natural-language
# questions from the terminal. Retrieved sources are printed after each answer.

# 0. SETUP ###################################

## 0.1 Load Packages ##########################

import os
import sys
import json
import time
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Force UTF-8 output on Windows to avoid encoding errors with special characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlite_vec import load as sqlite_vec_load, serialize_float32

## 0.2 Load Environment Variables ##############

# Load .env from project root (three levels up from this script)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

## 0.3 Configuration ##########################

# Ollama Cloud settings (same model used in app.py)
OLLAMA_URL = "https://ollama.com/api/chat"
OLLAMA_MODEL = "gpt-oss:20b-cloud"

# Embedding model settings (same as 05_embed.py)
EMBED_MODEL = "all-MiniLM-L6-v2"
VEC_DIM = 384  # all-MiniLM-L6-v2 output size

# SQLite database for vector embeddings (ephemeral, rebuilt each run)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_guardian.db")

# Countries available for analysis (same as app.py)
COUNTRIES = [
    "United States", "United Kingdom", "China", "India", "Russia",
    "Brazil", "Germany", "France", "Australia", "Japan",
]


# 1. HELPER FUNCTIONS #########################

## 1.1 Ollama Cloud LLM Call ##################

def agent_run(role, task, model=OLLAMA_MODEL):
    """Send a prompt to Ollama Cloud and return the response text."""
    if not OLLAMA_API_KEY:
        raise ValueError("OLLAMA_API_KEY not found in .env file.")

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": role},
            {"role": "user", "content": task},
        ],
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(OLLAMA_URL, headers=headers, json=body, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


## 1.2 Guardian API Query #####################

def query_guardian(country, from_date, to_date, api_key):
    """
    Query the Guardian API for articles mentioning a country.
    Returns (list of article dicts, total count, error message or None).
    Now also fetches trailText, headline, and shortUrl for RAG.
    """
    try:
        response = requests.get(
            "https://content.guardianapis.com/search",
            params={
                "q": country,
                "from-date": from_date,
                "to-date": to_date,
                "page-size": 50,
                "show-fields": "wordcount,trailText,headline,shortUrl",
                "api-key": api_key,
            },
            timeout=15,
        )

        if response.status_code == 401: return [], 0, "Invalid API key"
        if response.status_code == 429: return [], 0, "Rate limit exceeded"
        if response.status_code != 200: return [], 0, f"HTTP {response.status_code}"

        data = response.json()
        resp = data.get("response", {})

        if resp.get("status") != "ok":
            return [], 0, f"API error: {resp.get('message', 'Unknown')}"

        total = resp.get("total", 0)
        articles = []

        for article in resp.get("results", []):
            fields = article.get("fields", {})
            trail_text = fields.get("trailText", "")
            # Strip any HTML tags from trailText (it can contain <a> tags)
            trail_text = re.sub(r"<[^>]+>", "", trail_text)

            articles.append({
                "country": country,
                "headline": fields.get("headline", article.get("webTitle", "N/A")),
                "trail_text": trail_text,
                "short_url": fields.get("shortUrl", article.get("webUrl", "")),
                "section": article.get("sectionName", "N/A"),
                "date": article.get("webPublicationDate", "")[:10],
                "wordcount": int(fields.get("wordcount", "0") or 0),
            })

        return articles, total, None

    except requests.exceptions.Timeout:
        return [], 0, "Request timed out"
    except requests.exceptions.ConnectionError:
        return [], 0, "Connection failed"
    except Exception as e:
        return [], 0, str(e)


## 1.3 Embedding Functions ####################

# Global model instance (loaded once on first use)
_embed_model = None

def get_embed_model():
    """Load the sentence-transformers model (cached after first call)."""
    global _embed_model
    if _embed_model is None:
        print(f"Loading embedding model '{EMBED_MODEL}'...")
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model

def embed(text):
    """Encode a text string into a 384-dim float vector."""
    m = get_embed_model()
    vec = m.encode(text)
    return vec.tolist()


## 1.4 Build Embedding Index ##################

def build_index(conn, articles):
    """
    Embed each article and insert into the database.
    The text we embed is: headline + " | " + trail_text
    Metadata (headline, trail_text, short_url, country, section, date) is
    stored in the chunks table so we can retrieve it after search.
    """
    n = len(articles)
    print(f"Embedding {n} articles with {EMBED_MODEL}...")
    start = time.perf_counter()

    for i, art in enumerate(articles):
        # Combine headline and trail text for richer embeddings
        text = f"{art['headline']} | {art['trail_text']}"
        vec = embed(text)
        blob = serialize_float32(vec)

        # Insert metadata into chunks table
        conn.execute(
            """INSERT INTO chunks (id, text, headline, trail_text,
               short_url, country, section, date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (i, text, art["headline"], art["trail_text"],
             art["short_url"], art["country"], art["section"], art["date"]),
        )
        # Insert embedding into vec_chunks virtual table
        conn.execute(
            "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
            (i, blob),
        )

    conn.commit()
    elapsed = time.perf_counter() - start
    print(f"Embedded {n} articles in {elapsed:.1f} seconds.\n")


## 1.5 Semantic Search ########################

def search(conn, query, k=5):
    """
    Perform KNN semantic search on the vector index.
    Returns the top-k most relevant articles with metadata.
    """
    query_vec = embed(query)
    query_blob = serialize_float32(query_vec)

    # KNN search inside sqlite-vec
    cur = conn.execute(
        """SELECT rowid, distance
           FROM vec_chunks
           WHERE embedding MATCH ?
           ORDER BY distance
           LIMIT ?""",
        (query_blob, k),
    )
    rows = cur.fetchall()
    if not rows:
        return []

    results = []
    for rowid, distance in rows:
        row = conn.execute(
            """SELECT text, headline, trail_text, short_url,
                      country, section, date
               FROM chunks WHERE id = ?""",
            (rowid,),
        ).fetchone()

        results.append({
            "id": rowid,
            "score": round(1 - distance, 4),
            "text": row[0],
            "headline": row[1],
            "trail_text": row[2],
            "short_url": row[3],
            "country": row[4],
            "section": row[5],
            "date": row[6],
        })

    return results


## 1.6 Database Connection ####################

def connect_db(path=DB_PATH):
    """Connect to SQLite and load the sqlite-vec extension."""
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    sqlite_vec_load(conn)
    conn.enable_load_extension(False)
    return conn


def reset_rag_schema(conn):
    """
    Create or replace chunks + vec_chunks tables for a fresh embedding index.
    Call before build_index(conn, articles) on an empty or reused connection.
    """
    conn.execute("DROP TABLE IF EXISTS vec_chunks")
    conn.execute("DROP TABLE IF EXISTS chunks")
    conn.execute("""
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            headline TEXT,
            trail_text TEXT,
            short_url TEXT,
            country TEXT,
            section TEXT,
            date TEXT
        )
    """)
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks "
        f"USING vec0(embedding float[{VEC_DIM}] distance_metric=cosine)"
    )
    conn.commit()


# 2. DATA FETCHING WORKFLOW ###################

if __name__ == "__main__":
    print("=" * 60)
    print("  Guardian RAG -- Semantic Search over News Articles")
    print("=" * 60)

    # Check for required API keys
    if not GUARDIAN_API_KEY:
        print("ERROR: GUARDIAN_API_KEY not found in .env file.")
        exit(1)
    if not OLLAMA_API_KEY:
        print("ERROR: OLLAMA_API_KEY not found in .env file.")
        exit(1)

    # Show available countries
    print("\nAvailable countries:")
    for i, c in enumerate(COUNTRIES, 1):
        print(f"  {i:2d}. {c}")

    # Let user pick countries (or press Enter for all)
    selection = input(
        "\nEnter country numbers separated by commas (or press Enter for all): "
    ).strip()

    if selection:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            selected_countries = [COUNTRIES[i] for i in indices]
        except (ValueError, IndexError):
            print("Invalid input. Using all countries.")
            selected_countries = COUNTRIES
    else:
        selected_countries = COUNTRIES

    # Let user set date range (default: last 7 days)
    default_to = datetime.now().strftime("%Y-%m-%d")
    default_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    from_date = input(f"From date [{default_from}]: ").strip() or default_from
    to_date = input(f"To date   [{default_to}]: ").strip() or default_to

    # Fetch articles for each selected country
    print(f"\nFetching articles from {from_date} to {to_date}...")
    all_articles = []
    for country in selected_countries:
        articles, total, error = query_guardian(country, from_date, to_date, GUARDIAN_API_KEY)
        if error:
            print(f"  {country}: ERROR - {error}")
        else:
            all_articles.extend(articles)
            print(f"  {country}: {len(articles)} articles (of {total} total)")

    if not all_articles:
        print("\nNo articles fetched. Exiting.")
        exit(1)

    print(f"\nFetched {len(all_articles)} articles across {len(selected_countries)} countries.")

    # 3. BUILD EMBEDDING INDEX ####################

    # Remove old database if it exists (fresh index each run)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = connect_db(DB_PATH)
    reset_rag_schema(conn)

    # Embed all articles and build the index
    build_index(conn, all_articles)

    # 4. INTERACTIVE RAG LOOP ####################

    print("=" * 60)
    print("  RAG is ready! Ask questions about the articles.")
    print("  Type 'quit' or 'exit' to stop.")
    print("=" * 60)

    # System prompt for the LLM
    ROLE = (
        "You are a media analyst assistant specializing in Guardian newspaper coverage. "
        "Answer using ONLY the Guardian article excerpts provided as context. "
        "Write prose only: do NOT add inline citations—no markdown links, no 【bracketed headlines】, "
        "no footnotes, and no source titles after sentences; sources are listed separately below. "
        "If the context does not contain enough information to answer, say so explicitly. "
        "Use formal language. Be concise but thorough."
    )

    while True:
        print()
        query = input("Ask a question (or 'quit'): ").strip()
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not query:
            continue

        # Step 1: Retrieve the top-5 most relevant articles
        results = search(conn, query, k=5)

        if not results:
            print("No relevant articles found.")
            continue

        # Step 2: Format context for the LLM
        context_parts = []
        for r in results:
            context_parts.append(
                f"- Headline: {r['headline']}\n"
                f"  Summary: {r['trail_text']}\n"
                f"  Country: {r['country']} | Section: {r['section']} | Date: {r['date']}\n"
                f"  URL: {r['short_url']}\n"
                f"  Relevance score: {r['score']}"
            )
        context = "\n\n".join(context_parts)
        task = f"QUESTION: {query}\n\nARTICLE CONTEXT:\n{context}"

        # Step 3: Send to LLM and print the answer
        print("\nGenerating answer...\n")
        try:
            answer = agent_run(role=ROLE, task=task, model=OLLAMA_MODEL)
            print("-" * 60)
            print("ANSWER:")
            print("-" * 60)
            print(answer)
        except Exception as e:
            print(f"LLM Error: {e}")
            continue

        # Step 4: Print the source articles used
        print("\n" + "-" * 60)
        print("SOURCES:")
        print("-" * 60)
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['headline']}")
            print(f"     {r['trail_text'][:120]}{'...' if len(r['trail_text']) > 120 else ''}")
            print(f"     {r['short_url']}")
            print()

    conn.close()
    print("Database connection closed.")
