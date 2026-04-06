# rag_guardian.py
# Semantic RAG with Guardian API Articles
# Pairs with app.py (Guardian News Coverage Analyzer)
# Tim Fraser / Nairv

# This module provides Guardian article fetch (with trail text), embedding,
# sqlite-vec KNN search, and RAG answers via Ollama Cloud. Import from app.py
# or run as a CLI script.

# 0. SETUP ###################################

## 0.1 Load Packages ##########################

import os
import sys
import re
import sqlite3
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import requests
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sqlite_vec import load as sqlite_vec_load, serialize_float32

## 0.2 Load Environment Variables ##############

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

## 0.3 Configuration ##########################

OLLAMA_URL = "https://ollama.com/api/chat"
OLLAMA_MODEL = "gpt-oss:20b-cloud"

EMBED_MODEL = "all-MiniLM-L6-v2"
VEC_DIM = 384

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_guardian.db")

COUNTRIES = [
    "United States", "United Kingdom", "China", "India", "Russia",
    "Brazil", "Germany", "France", "Australia", "Japan",
]

RAG_SYSTEM_PROMPT = (
    "You are a media analyst assistant specializing in Guardian newspaper coverage. "
    "Answer the user's question using ONLY the Guardian article excerpts provided as context. "
    "For each claim you make, cite the source article by its headline and shortUrl "
    "in this format: [Headline](shortUrl). "
    "If the context does not contain enough information to answer, say so explicitly. "
    "Use formal language. Be concise but thorough."
)


# 1. HELPER FUNCTIONS #########################

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


def query_guardian(country, from_date, to_date, api_key):
    """
    Query the Guardian API for articles mentioning a country.
    Returns (list of article dicts, total count, error message or None).
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


_embed_model = None


def get_embed_model():
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(EMBED_MODEL)
    return _embed_model


def embed(text):
    m = get_embed_model()
    vec = m.encode(text)
    return vec.tolist()


def build_index(conn, articles):
    for i, art in enumerate(articles):
        text = f"{art['headline']} | {art['trail_text']}"
        vec = embed(text)
        blob = serialize_float32(vec)

        conn.execute(
            """INSERT INTO chunks (id, text, headline, trail_text,
               short_url, country, section, date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (i, text, art["headline"], art["trail_text"],
             art["short_url"], art["country"], art["section"], art["date"]),
        )
        conn.execute(
            "INSERT INTO vec_chunks (rowid, embedding) VALUES (?, ?)",
            (i, blob),
        )

    conn.commit()


def search(conn, query, k=5):
    query_vec = embed(query)
    query_blob = serialize_float32(query_vec)

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


def connect_db(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.enable_load_extension(True)
    sqlite_vec_load(conn)
    conn.enable_load_extension(False)
    return conn


def ensure_rag_schema(conn):
    """Create empty chunks + vec_chunks tables (drops prior vec table)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
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
    conn.execute("DROP TABLE IF EXISTS vec_chunks")
    conn.execute(
        f"CREATE VIRTUAL TABLE vec_chunks "
        f"USING vec0(embedding float[{VEC_DIM}] distance_metric=cosine)"
    )
    conn.execute("DELETE FROM chunks")
    conn.commit()


def collect_articles_for_rag(countries, from_date, to_date, api_key):
    """Fetch RAG-ready articles (headline, trail, short URL) for each country."""
    if not api_key:
        return [], "Missing GUARDIAN_API_KEY"
    all_articles = []
    errors = []
    for country in countries:
        articles, _total, err = query_guardian(country, from_date, to_date, api_key)
        if err:
            errors.append(f"{country}: {err}")
        elif articles:
            all_articles.extend(articles)
    if not all_articles:
        return [], "; ".join(errors) if errors else "No articles retrieved"
    return all_articles, None


def rebuild_rag_index(articles, db_path=None):
    """
    Replace the SQLite vector index at db_path with embeddings for articles.
    Returns (db_path, None) on success or (db_path, error_message) on failure.
    """
    path = db_path or DB_PATH
    if not articles:
        return path, "No articles to index"
    try:
        if os.path.exists(path):
            os.remove(path)
        conn = connect_db(path)
        ensure_rag_schema(conn)
        build_index(conn, articles)
        conn.close()
        return path, None
    except Exception as e:
        return path, str(e)


def format_rag_context(results):
    parts = []
    for r in results:
        parts.append(
            f"- Headline: {r['headline']}\n"
            f"  Summary: {r['trail_text']}\n"
            f"  Country: {r['country']} | Section: {r['section']} | Date: {r['date']}\n"
            f"  URL: {r['short_url']}\n"
            f"  Relevance score: {r['score']}"
        )
    return "\n\n".join(parts)


def rag_answer(db_path, user_question, k=5, model=None):
    """
    Retrieve top-k chunks and generate an answer with Ollama Cloud.
    Returns dict: answer (str), sources (list), error (str or None).
    """
    if not user_question or not user_question.strip():
        return {"answer": "", "sources": [], "error": "Empty question"}
    if not os.path.exists(db_path):
        return {"answer": "", "sources": [], "error": "RAG index not built. Build the index first."}
    if not OLLAMA_API_KEY:
        return {"answer": "", "sources": [], "error": "OLLAMA_API_KEY not set"}

    conn = connect_db(db_path)
    try:
        results = search(conn, user_question.strip(), k=k)
        if not results:
            return {"answer": "No relevant articles found in the index.", "sources": [], "error": None}

        context = format_rag_context(results)
        task = f"QUESTION: {user_question}\n\nARTICLE CONTEXT:\n{context}"
        mdl = model or OLLAMA_MODEL
        answer = agent_run(role=RAG_SYSTEM_PROMPT, task=task, model=mdl)
        return {"answer": answer, "sources": results, "error": None}
    except Exception as e:
        return {"answer": "", "sources": [], "error": str(e)}
    finally:
        conn.close()


# 2. CLI ###################################

if __name__ == "__main__":
    from datetime import datetime, timedelta

    print("=" * 60)
    print("  Guardian RAG -- Semantic Search over News Articles")
    print("=" * 60)

    if not GUARDIAN_API_KEY:
        print("ERROR: GUARDIAN_API_KEY not found in .env file.")
        sys.exit(1)
    if not OLLAMA_API_KEY:
        print("ERROR: OLLAMA_API_KEY not found in .env file.")
        sys.exit(1)

    print("\nAvailable countries:")
    for i, c in enumerate(COUNTRIES, 1):
        print(f"  {i:2d}. {c}")

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

    default_to = datetime.now().strftime("%Y-%m-%d")
    default_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    from_date = input(f"From date [{default_from}]: ").strip() or default_from
    to_date = input(f"To date   [{default_to}]: ").strip() or default_to

    print(f"\nFetching articles from {from_date} to {to_date}...")
    all_articles, err = collect_articles_for_rag(selected_countries, from_date, to_date, GUARDIAN_API_KEY)
    if err:
        print(f"ERROR: {err}")
        sys.exit(1)

    by_country = Counter(a["country"] for a in all_articles)
    for country in selected_countries:
        n = by_country.get(country, 0)
        print(f"  {country}: {n} articles in index")

    print(f"\nFetched {len(all_articles)} articles across {len(selected_countries)} countries.")

    _path, berr = rebuild_rag_index(all_articles, DB_PATH)
    if berr:
        print(f"Index error: {berr}")
        sys.exit(1)

    print("=" * 60)
    print("  RAG is ready! Ask questions about the articles.")
    print("  Type 'quit' or 'exit' to stop.")
    print("=" * 60)

    conn = connect_db(DB_PATH)
    try:
        while True:
            print()
            query = input("Ask a question (or 'quit'): ").strip()
            if query.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            if not query:
                continue

            results = search(conn, query, k=5)
            if not results:
                print("No relevant articles found.")
                continue

            context = format_rag_context(results)
            task = f"QUESTION: {query}\n\nARTICLE CONTEXT:\n{context}"
            print("\nGenerating answer...\n")
            try:
                answer = agent_run(role=RAG_SYSTEM_PROMPT, task=task, model=OLLAMA_MODEL)
                print("-" * 60)
                print("ANSWER:")
                print("-" * 60)
                print(answer)
            except Exception as e:
                print(f"LLM Error: {e}")
                continue

            print("\n" + "-" * 60)
            print("SOURCES:")
            print("-" * 60)
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r['headline']}")
                print(f"     {r['short_url']}")
                print()
    finally:
        conn.close()
        print("Database connection closed.")
