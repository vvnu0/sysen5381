# app.py
# Integrated AI-Powered Geographic Attention Reporter
# Combines Guardian API, Shiny Dashboard, and Ollama AI Insights
# Tim Fraser

# This application demonstrates:
# - LAB 1: Guardian API integration for geographic news coverage data
# - LAB 2: Interactive Shiny dashboard with charts and data tables
# - LAB 3: AI-powered reporting via Ollama with insights generation

# 0. Setup #################################

## 0.1 Load Packages ############################

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import pandas as pd
import requests
from dotenv import load_dotenv

import plotly.express as px

from shiny import reactive, render
from shiny.express import input, ui

# RAG + multi-agent chatbot (same folder as this app)
from rag_guardian import (
    query_guardian as rag_query_guardian,
    build_index,
    search as rag_search,
    connect_db as rag_connect_db,
    reset_rag_schema,
)
from agent_workflow import cloud_agent_run, tool_search_guardian_articles

## 0.2 Load Environment Variables ################

# Load .env from project root (three levels up from this app)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
_dotenv_loaded = load_dotenv(dotenv_path=env_path)
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")

## 0.3 Ollama Cloud Configuration ################

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_URL = "https://ollama.com/api/chat"
OLLAMA_MODEL = "gpt-oss:20b-cloud"

## 0.4 Constants #################################

# Countries to analyze for geographic coverage
COUNTRIES = [
    "United States", "United Kingdom", "China", "India", "Russia",
    "Brazil", "Germany", "France", "Australia", "Japan",
]

# Population data in millions (for per-capita calculations)
POPULATIONS = {
    "United States": 334, "United Kingdom": 68, "China": 1425,
    "India": 1438, "Russia": 144, "Brazil": 216,
    "Germany": 84, "France": 68, "Australia": 26, "Japan": 124,
}

# Map Guardian sectionId values to broad topic categories
TOPIC_MAP = {
    "politics": "Politics", "world": "Politics", "us-news": "Politics",
    "uk-news": "Politics", "australia-news": "Politics", "law": "Politics",
    "global": "Politics",
    "culture": "Culture", "music": "Culture", "film": "Culture",
    "books": "Culture", "artanddesign": "Culture", "stage": "Culture",
    "tv-and-radio": "Culture", "games": "Culture", "food": "Culture",
    "environment": "Crisis", "global-development": "Crisis",
    "society": "Crisis", "inequality": "Crisis",
    "sport": "Sport", "football": "Sport", "cricket": "Sport",
    "rugby-union": "Sport", "tennis": "Sport", "cycling": "Sport",
    "formulaone": "Sport",
    "business": "Business", "technology": "Business",
    "money": "Business", "media": "Business",
    "science": "Science", "lifeandstyle": "Science", "education": "Science",
}

# Color palette for topics
TOPIC_COLORS = {
    "Politics": "#007AFF", "Culture": "#FF3B30", "Crisis": "#FF9500",
    "Sport": "#34C759", "Business": "#AF52DE", "Science": "#5AC8FA",
    "Other": "#8E8E93",
}


# 1. Helper Functions ##############################

def classify_topic(section_id):
    """Classify a Guardian sectionId into a broad topic category."""
    return TOPIC_MAP.get(section_id.lower(), "Other") if section_id else "Other"


def query_guardian(country, from_date, to_date, api_key):
    """
    Query the Guardian API for articles mentioning a country.
    Returns a tuple: (list of article dicts, total count, error message or None).
    """
    try:
        response = requests.get(
            "https://content.guardianapis.com/search",
            params={
                "q": country,
                "from-date": from_date,
                "to-date": to_date,
                "page-size": 50,
                "show-fields": "wordcount",
                "api-key": api_key,
            },
            timeout=15,
        )
        
        if response.status_code == 401:
            return [], 0, "Invalid API key"
        if response.status_code == 429:
            return [], 0, "Rate limit exceeded"
        if response.status_code != 200:
            return [], 0, f"HTTP {response.status_code}"
        
        data = response.json()
        resp = data.get("response", {})
        
        if resp.get("status") != "ok":
            return [], 0, f"API error: {resp.get('message', 'Unknown')}"
        
        total = resp.get("total", 0)
        articles = []
        
        for article in resp.get("results", []):
            section_id = article.get("sectionId", "")
            fields = article.get("fields", {})
            wordcount = fields.get("wordcount", "0")
            
            articles.append({
                "country": country,
                "title": article.get("webTitle", "N/A"),
                "section": article.get("sectionName", "N/A"),
                "section_id": section_id,
                "topic": classify_topic(section_id),
                "pillar": article.get("pillarName", "Other"),
                "wordcount": int(wordcount) if wordcount else 0,
                "date": article.get("webPublicationDate", "")[:10],
                "url": article.get("webUrl", ""),
            })
        
        return articles, total, None
    
    except requests.exceptions.Timeout:
        return [], 0, "Request timed out"
    except requests.exceptions.ConnectionError:
        return [], 0, "Connection failed"
    except Exception as e:
        return [], 0, str(e)


def format_data_for_ai(df_summary, df_articles, from_date, to_date):
    """Format the data as structured text for AI consumption."""
    
    total_articles = df_summary["total_articles"].sum()
    avg_articles = df_summary["total_articles"].mean()
    top_country = df_summary.iloc[0]["country"]
    bottom_country = df_summary.iloc[-1]["country"]
    
    # Calculate average wordcount per country
    wordcount_by_country = (df_articles
        .groupby("country")["wordcount"]
        .mean()
        .round(0)
        .to_dict()
    )
    
    # Calculate pillar distribution
    pillar_counts = (df_articles
        .groupby(["country", "pillar"])
        .size()
        .unstack(fill_value=0)
    )
    pillar_pct = pillar_counts.div(pillar_counts.sum(axis=1), axis=0) * 100
    pillar_pct = pillar_pct.round(1)
    
    # Build data text
    data_text = f"""DATA SUMMARY:
- Date range: {from_date} to {to_date}
- Countries analyzed: {len(df_summary)}
- Total articles: {total_articles:,}
- Average per country: {avg_articles:,.0f}

COVERAGE BY COUNTRY (sorted by volume):
"""
    
    for _, row in df_summary.iterrows():
        country = row["country"]
        avg_wc = wordcount_by_country.get(country, 0)
        news_pct = pillar_pct.loc[country, "News"] if country in pillar_pct.index and "News" in pillar_pct.columns else 0
        opinion_pct = pillar_pct.loc[country, "Opinion"] if country in pillar_pct.index and "Opinion" in pillar_pct.columns else 0
        
        data_text += f"- {country}: {row['total_articles']:,} articles, "
        data_text += f"{row['articles_per_1m']:.1f} per 1M pop, "
        data_text += f"avg {avg_wc:.0f} words, "
        data_text += f"{news_pct:.0f}% News, {opinion_pct:.0f}% Opinion\n"
    
    data_text += f"""
KEY OBSERVATIONS:
- Highest coverage: {top_country} ({df_summary.iloc[0]['total_articles']:,} articles)
- Lowest coverage: {bottom_country} ({df_summary.iloc[-1]['total_articles']:,} articles)
- Coverage ratio (top/bottom): {df_summary.iloc[0]['total_articles'] / max(df_summary.iloc[-1]['total_articles'], 1):.1f}x
"""
    
    return data_text


def query_ollama(data_text):
    """Send data to Ollama Cloud and return AI-generated analysis."""
    
    if not OLLAMA_API_KEY:
        return "Error: OLLAMA_API_KEY not found in .env file. Please set it up first."
    
    prompt = f"""ROLE: You are a media analyst specializing in global news coverage patterns.

TASK: Analyze the following Guardian newspaper coverage data and produce a concise analytical report.

INSTRUCTIONS:
- USE FORMAL LANGUAGE ONLY. No hyperbole or superlatives.
- REPORT SPECIFIC NUMBERS AND PERCENTAGES from the data.
- DO NOT use phrases like "it is clear that", "obviously", or "interestingly".
- PROVIDE EXACTLY 2 DEEP INSIGHTS that go beyond restating the data.
- EXTEND EACH INSIGHT with your own analysis, implications, or tangential observations.
- FORMAT: Use markdown headers and bullet points. Keep response under 300 words.

CHAIN OF THOUGHT:
1. First, identify the top and bottom countries by raw coverage volume.
2. Compare raw coverage vs per-capita coverage to find discrepancies.
3. Analyze coverage DEPTH: Which countries get longer articles (higher avg wordcount)?
4. Analyze coverage TONE: Which countries appear more in News vs Opinion pillars?
5. Consider explanatory factors (Guardian's UK base, geopolitical relevance, crisis events).
6. Draw conclusions about media attention patterns and potential biases.

{data_text}

OUTPUT FORMAT:

## Key Statistics
- [3-4 bullet points with specific numbers from the data]

## Insight 1: [Descriptive Title]
[2-3 sentences providing deep analysis, not just restating numbers]

## Insight 2: [Descriptive Title]
[2-3 sentences providing deep analysis with implications or tangents]

## Implications
[1-2 sentences on what this means for journalists, researchers, or readers]
"""
    
    body = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    
    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(OLLAMA_URL, headers=headers, json=body, timeout=120)
        
        if response.status_code != 200:
            return f"Error: Ollama Cloud returned status {response.status_code}. Check your API key and quota."
        
        result = response.json()
        if "message" not in result or "content" not in result["message"]:
            return "Error: Unexpected response format from Ollama Cloud."
        
        return result["message"]["content"]
    
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to Ollama Cloud. Check your network connection."
    except Exception as e:
        return f"Error: {str(e)}"


# 1b. Dashboard RAG index + chatbot pipeline ################

DASHBOARD_RAG_DB = Path(__file__).resolve().parent / "dashboard_rag.db"
_dashboard_rag_conn = None


def _close_dashboard_rag():
    """Close the SQLite connection used for the dashboard RAG index."""
    global _dashboard_rag_conn
    if _dashboard_rag_conn is not None:
        try:
            _dashboard_rag_conn.close()
        except Exception:
            pass
        _dashboard_rag_conn = None


def _extract_articles_from_planner(result1):
    """Parse tool output from Agent 1 (search_guardian_articles)."""
    if not result1:
        return [], "No response from the query planner."
    if not isinstance(result1, list):
        return [], "Unexpected response from the query planner."
    for tc in result1:
        out = tc.get("output")
        if not isinstance(out, list) or not out:
            continue
        if not isinstance(out[0], dict):
            continue
        if "error" in out[0]:
            return [], str(out[0].get("error", "Guardian API error"))
        return out, None
    return [], (
        "The model did not retrieve articles. Try naming a country "
        f"({', '.join(COUNTRIES[:3])}, …) and a time period (e.g. last week)."
    )


def run_guardian_chatbot(user_question):
    """
    Multi-agent + RAG: (1) LLM calls search_guardian_articles for country/dates,
    (2) embed articles and KNN search, (3) LLM answers with citations.
    Returns dict with keys: ok, answer, sources, meta, error.
    """
    if not OLLAMA_API_KEY:
        return {"ok": False, "error": "OLLAMA_API_KEY not set in .env."}
    if not GUARDIAN_API_KEY:
        return {"ok": False, "error": "GUARDIAN_API_KEY not set in .env."}
    q = (user_question or "").strip()
    if not q:
        return {"ok": False, "error": "Please enter a question."}

    today = datetime.now().strftime("%Y-%m-%d")
    role_parser = (
        "You plan Guardian API searches. "
        f"Today's date is {today} (YYYY-MM-DD). "
        "Interpret relative time: 'yesterday' = the previous calendar day only; "
        "'last week' = the 7 days ending yesterday; 'last month' ≈ 30 days ending yesterday. "
        "Map locations to EXACT country names from this list only: "
        f"{', '.join(COUNTRIES)}. "
        "Examples: US / America / USA → United States; UK / Britain → United Kingdom. "
        "You MUST call search_guardian_articles exactly once with "
        "country, from_date, and to_date (YYYY-MM-DD). "
        "Do not put topic keywords (e.g. basketball) in the tool — only country and dates."
    )

    try:
        result1 = cloud_agent_run(
            role=role_parser,
            task=q,
            tools=[tool_search_guardian_articles],
            output="tools",
            model=OLLAMA_MODEL,
        )
    except Exception as e:
        return {"ok": False, "error": f"Query planner failed: {e}"}

    articles, err = _extract_articles_from_planner(result1)
    if err:
        return {"ok": False, "error": err}

    conn = None
    try:
        conn = rag_connect_db(":memory:")
        reset_rag_schema(conn)
        build_index(conn, articles)
        hits = rag_search(conn, q, k=5)
    except Exception as e:
        return {"ok": False, "error": f"Semantic search failed: {e}"}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    if not hits:
        return {
            "ok": True,
            "answer": "No articles matched your question semantically in the retrieved set. "
            "Try a broader date range or different wording.",
            "sources": [],
            "meta": {},
        }

    context_parts = []
    for r in hits:
        context_parts.append(
            f"- Headline: {r['headline']}\n"
            f"  Summary: {r['trail_text']}\n"
            f"  Country: {r['country']} | Section: {r['section']} | Date: {r['date']}\n"
            f"  URL: {r['short_url']}\n"
            f"  Relevance score: {r['score']}"
        )
    context = "\n\n".join(context_parts)
    task = f"QUESTION: {q}\n\nARTICLE CONTEXT:\n{context}"

    role_analyst = (
        "You are a media analyst assistant specializing in Guardian newspaper coverage. "
        "Answer using ONLY the article excerpts provided. "
        "Write clean prose only: do NOT add inline citations of any kind—no markdown links, "
        "no 【bracketed headlines】, no footnote markers, and no source titles after sentences. "
        "The app shows matching articles in a separate Sources list; your reply must read like "
        "a standalone summary. If context is insufficient, say so clearly. Use formal, concise language."
    )

    try:
        answer = cloud_agent_run(
            role=role_analyst,
            task=task,
            tools=None,
            output="text",
            model=OLLAMA_MODEL,
        )
    except Exception as e:
        return {"ok": False, "error": f"Answer generation failed: {e}"}

    meta = {
        "articles_fetched": len(articles),
        "sources_used": len(hits),
    }
    return {"ok": True, "answer": answer, "sources": hits, "meta": meta}


# 2. Page Configuration ############################

# Set page title (compatible with older Shiny versions)
ui.tags.title("Geographic Attention Reporter")

# Apple-inspired design system
ui.tags.style("""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        --apple-blue: #007AFF;
        --apple-green: #34C759;
        --apple-orange: #FF9500;
        --apple-gray: #8E8E93;
        --apple-bg: #F5F5F7;
        --apple-card: #FFFFFF;
        --apple-text: #1D1D1F;
        --apple-text-secondary: #86868B;
        --apple-border: rgba(0,0,0,0.04);
        --apple-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --apple-shadow-hover: 0 4px 14px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);
        --apple-radius: 14px;
    }

    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display',
                     'Segoe UI', sans-serif !important;
        background-color: var(--apple-bg) !important;
        color: var(--apple-text) !important;
        -webkit-font-smoothing: antialiased;
    }

    /* Sidebar */
    .bslib-sidebar-layout > .sidebar {
        background: var(--apple-card) !important;
        border-right: 1px solid var(--apple-border) !important;
        box-shadow: 1px 0 8px rgba(0,0,0,0.03) !important;
    }
    .sidebar h4 {
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        letter-spacing: -0.01em !important;
        color: var(--apple-text) !important;
    }
    .sidebar hr {
        border-color: rgba(0,0,0,0.06) !important;
        margin: 1rem 0 !important;
    }
    .sidebar label {
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        color: var(--apple-text-secondary) !important;
        letter-spacing: 0.03em !important;
        text-transform: uppercase !important;
    }
    .sidebar .form-check-label {
        text-transform: none !important;
        font-weight: 400 !important;
        font-size: 0.9rem !important;
        color: var(--apple-text) !important;
    }

    /* Buttons */
    .btn-primary {
        background: var(--apple-blue) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 10px 20px !important;
        transition: all 0.2s ease !important;
        letter-spacing: -0.01em !important;
    }
    .btn-primary:hover {
        background: #0066D6 !important;
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(0,122,255,0.3) !important;
    }
    .btn-success {
        background: linear-gradient(135deg, #34C759, #30B350) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 10px 20px !important;
        transition: all 0.2s ease !important;
        letter-spacing: -0.01em !important;
    }
    .btn-success:hover {
        background: linear-gradient(135deg, #30B350, #28A745) !important;
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(52,199,89,0.3) !important;
    }

    /* Cards */
    .card {
        border: 1px solid var(--apple-border) !important;
        border-radius: var(--apple-radius) !important;
        box-shadow: var(--apple-shadow) !important;
        transition: box-shadow 0.3s ease !important;
        overflow: hidden !important;
        background: var(--apple-card) !important;
    }
    .card:hover {
        box-shadow: var(--apple-shadow-hover) !important;
    }
    .card-header {
        background: transparent !important;
        border-bottom: 1px solid rgba(0,0,0,0.04) !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        color: var(--apple-text) !important;
        padding: 16px 20px !important;
        letter-spacing: -0.01em !important;
    }

    /* Value Boxes */
    .bslib-value-box {
        border-radius: var(--apple-radius) !important;
        border: none !important;
        box-shadow: var(--apple-shadow) !important;
        overflow: hidden !important;
    }
    .bslib-value-box .value-box-title {
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        opacity: 0.85;
    }
    .bslib-value-box .value-box-value {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }
    .bg-primary {
        background: linear-gradient(135deg, #007AFF, #5856D6) !important;
    }
    .bg-info {
        background: linear-gradient(135deg, #5AC8FA, #007AFF) !important;
    }
    .bg-success {
        background: linear-gradient(135deg, #34C759, #30D158) !important;
    }

    /* Form inputs */
    .form-control, .form-select {
        border-radius: 8px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        font-size: 0.9rem !important;
        padding: 8px 12px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .form-control:focus, .form-select:focus {
        border-color: var(--apple-blue) !important;
        box-shadow: 0 0 0 3px rgba(0,122,255,0.15) !important;
    }
    .form-check-input:checked {
        background-color: var(--apple-blue) !important;
        border-color: var(--apple-blue) !important;
    }

    /* Alert boxes */
    .alert {
        border-radius: 10px !important;
        border: none !important;
        font-size: 0.9rem !important;
    }

    /* Main content area */
    .bslib-sidebar-layout > .main {
        background-color: var(--apple-bg) !important;
        padding: 1.25rem !important;
        padding-top: 2.5rem !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.25); }

    /* Hero + chatbot */
    .hero-wrap {
        background: linear-gradient(135deg, #FFFFFF 0%, #F0F4FF 50%, #E8F4FC 100%);
        border-radius: var(--apple-radius);
        border: 1px solid rgba(0,122,255,0.12);
        box-shadow: var(--apple-shadow);
        padding: 1.75rem 1.5rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .hero-title {
        font-weight: 700;
        font-size: 1.35rem;
        letter-spacing: -0.02em;
        margin-bottom: 0.35rem;
        color: var(--apple-text);
    }
    .hero-sub {
        font-size: 0.88rem;
        color: var(--apple-text-secondary);
        margin-bottom: 1rem;
    }
    .hero-search-row {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        align-items: stretch;
    }
    .hero-search-row .form-group {
        flex: 1 1 220px;
        margin-bottom: 0 !important;
    }
    .hero-search-row .btn {
        flex: 0 0 auto;
        align-self: center;
        min-width: 110px;
    }
    .chat-response-card .card-header {
        background: linear-gradient(90deg, rgba(0,122,255,0.06), transparent) !important;
    }
    .chat-answer-md {
        line-height: 1.55;
        font-size: 0.95rem;
    }
    .source-card {
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 10px;
        padding: 0.85rem 1rem;
        margin: 0.5rem 1rem 0.75rem;
        background: #FAFAFA;
    }
    .source-headline { font-size: 0.95rem; margin-bottom: 0.25rem; }
    .source-link { color: var(--apple-blue) !important; text-decoration: none; font-weight: 600; }
    .source-link:hover { text-decoration: underline !important; }
    .source-meta { font-size: 0.75rem; color: var(--apple-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
    .source-trail { font-size: 0.85rem; color: var(--apple-text); margin: 0.5rem 0 0; line-height: 1.45; }
""")

# 3. Sidebar — Input Controls ######################

with ui.sidebar(open="desktop", width=300):
    ui.h4("Query Parameters")
    ui.hr()
    
    # Date range inputs (from_date is exactly 1 month before to_date)
    ui.input_date(
        "from_date", "From Date",
        value=(datetime.now() - relativedelta(months=1)).strftime("%Y-%m-%d"),
    )
    ui.input_date(
        "to_date", "To Date",
        value=datetime.now().strftime("%Y-%m-%d"),
    )
    
    ui.hr()
    
    # Country selection
    ui.input_checkbox_group(
        "countries", "Countries to Analyze",
        choices=COUNTRIES,
        selected=COUNTRIES,
    )
    
    ui.hr()
    
    # Fetch Data button with double-trigger fix
    ui.input_action_button(
        "run_query", "Fetch Data", class_="btn-primary w-100",
    )
    
    # JavaScript to trigger button twice (fixes chart rendering on first click)
    ui.tags.script("""
        (function() {
            let isSecondClick = false;
            document.addEventListener('click', function(e) {
                if (e.target && e.target.id === 'run_query' && !isSecondClick) {
                    isSecondClick = true;
                    setTimeout(function() {
                        document.getElementById('run_query').click();
                        isSecondClick = false;
                    }, 150);
                }
            }, true);
        })();
    """)
    
    ui.br()
    ui.br()
    
    # Generate AI Report button
    ui.input_action_button(
        "generate_ai", "Generate AI Report", class_="btn-success w-100",
    )
    
    ui.hr()
    ui.markdown(
        "*Data: [The Guardian](https://open-platform.theguardian.com/) | "
        "AI: [Ollama](https://ollama.ai/)*"
    )

# 4. Reactive Data — Fetch & Process ###############

@reactive.calc
@reactive.event(input.run_query)
def fetch_data():
    """Query Guardian API for each selected country when button is clicked."""
    global _dashboard_rag_conn
    try:
        # Check for API key
        if not GUARDIAN_API_KEY:
            return {"error": "GUARDIAN_API_KEY not found in .env file. Please add it and restart."}
        
        # Check for selected countries
        selected = list(input.countries())
        if not selected:
            return {"error": "Please select at least one country to analyze."}
        
        from_date = str(input.from_date())
        to_date = str(input.to_date())
        
        # Validate date range
        if from_date >= to_date:
            return {"error": "From date must be before to date."}
        
        all_articles = []
        totals = {}
        failed_countries = []
        error_messages = []
        
        # Query each country
        for country in selected:
            articles, total, error = query_guardian(country, from_date, to_date, GUARDIAN_API_KEY)
            if error:
                failed_countries.append(country)
                error_messages.append(f"{country}: {error}")
            elif articles:
                all_articles.extend(articles)
                totals[country] = total
            else:
                failed_countries.append(country)
                error_messages.append(f"{country}: No articles found")
        
        # Check if all countries failed
        if len(failed_countries) == len(selected):
            return {"error": f"Failed to fetch data for all countries. {'; '.join(error_messages)}"}
        
        # Check if we got any data
        if not all_articles:
            return {"error": "No articles found for the selected criteria."}
        
        df_articles = pd.DataFrame(all_articles)
        
        df_summary = (pd.DataFrame(
                [{"country": c, "total_articles": totals.get(c, 0)} for c in selected]
            )
            .assign(
                population_m=lambda x: x["country"].map(POPULATIONS),
                articles_per_1m=lambda x: (x["total_articles"] / x["population_m"]).round(1),
            )
            .sort_values("total_articles", ascending=False)
        )
        
        result = {
            "articles": df_articles,
            "summary": df_summary,
            "from_date": from_date,
            "to_date": to_date,
        }
        
        # Add warning if some countries failed
        if failed_countries:
            warning_detail = "; ".join(error_messages) if error_messages else ", ".join(failed_countries)
            result["warning"] = f"Partial failure: {warning_detail}"

        # Build semantic RAG index for sidebar date range (headlines + trail text)
        try:
            _close_dashboard_rag()
            rag_articles = []
            for country in selected:
                arts, _, rag_err = rag_query_guardian(country, from_date, to_date, GUARDIAN_API_KEY)
                if not rag_err and arts:
                    rag_articles.extend(arts)
            if rag_articles:
                if DASHBOARD_RAG_DB.exists():
                    DASHBOARD_RAG_DB.unlink()
                _dashboard_rag_conn = rag_connect_db(str(DASHBOARD_RAG_DB))
                reset_rag_schema(_dashboard_rag_conn)
                build_index(_dashboard_rag_conn, rag_articles)
                result["rag_chunks"] = len(rag_articles)
            else:
                result["rag_warning"] = "No RAG articles indexed (empty API results)."
        except Exception as ex:
            result["rag_warning"] = f"RAG index not built: {ex}"
        
        return result
        
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}


@reactive.calc
@reactive.event(input.generate_ai)
def generate_ai_report():
    """Generate AI analysis from the fetched data."""
    try:
        data = fetch_data()
        if not data:
            return "**Error:** No data available. Please click 'Fetch Data' first."
        if "error" in data:
            return f"**Error:** {data['error']}"
        
        data_text = format_data_for_ai(
            data["summary"],
            data["articles"],
            data["from_date"],
            data["to_date"],
        )
        
        return query_ollama(data_text)
    except Exception as e:
        return f"**Error generating report:** {str(e)}"


# 5. Main Panel — Dashboard Layout #################

# API key warning
if not GUARDIAN_API_KEY:
    ui.notification_show(
        "GUARDIAN_API_KEY not found in .env file. Please add it and restart.",
        type="error",
        duration=None,
    )

if not OLLAMA_API_KEY:
    ui.notification_show(
        "OLLAMA_API_KEY not found in .env file. Chatbot and AI report need it.",
        type="warning",
        duration=None,
    )

# Hero: natural-language Guardian search (independent of sidebar dates)
with ui.div(class_="hero-wrap"):
    ui.tags.div("Ask The Guardian", class_="hero-title")
    ui.tags.p(
        "Ask in plain English about any country and time period. "
        "An agent picks dates and fetches articles, then semantic search finds the best excerpts.",
        class_="hero-sub",
    )
    ui.tags.div(
        ui.input_text(
            "chat_query",
            label="",
            placeholder="e.g. What was happening in basketball in the United States last week?",
            width="100%",
        ),
        ui.input_action_button(
            "ask_guardian",
            "Search",
            class_="btn-primary",
        ),
        class_="hero-search-row",
    )


@reactive.calc
@reactive.event(input.ask_guardian)
def guardian_chat_result():
    """Run multi-agent + RAG pipeline when the user clicks Search."""
    return run_guardian_chatbot(input.chat_query())


with ui.card(class_="mb-4 chat-response-card"):
    ui.card_header(ui.tags.i(class_="fa-solid fa-robot me-2"), "Assistant")

    @render.ui
    def guardian_chat_ui():
        if input.ask_guardian() == 0:
            return ui.div(
                ui.p(
                    "Results appear here after you click Search. "
                    "Citations link to Guardian articles.",
                    class_="text-muted p-4",
                ),
                class_="p-1",
            )
        res = guardian_chat_result()
        if not res.get("ok"):
            return ui.div(
                ui.tags.div(
                    ui.tags.i(class_="fa-solid fa-circle-exclamation me-2"),
                    res.get("error", "Something went wrong."),
                    class_="alert alert-warning m-3",
                )
            )
        blocks = [
            ui.div(ui.markdown(res["answer"]), class_="p-3 chat-answer-md"),
        ]
        srcs = res.get("sources") or []
        if srcs:
            blocks.append(ui.h5("Sources", class_="px-3 pt-2 mb-0"))
            for i, s in enumerate(srcs, 1):
                headline = s.get("headline") or "Article"
                link = s.get("short_url") or "#"
                trail_full = s.get("trail_text") or ""
                trail = trail_full[:220] + ("…" if len(trail_full) > 220 else "")
                src_children = [
                    ui.tags.div(
                        ui.tags.strong(f"{i}. "),
                        ui.tags.a(
                            headline,
                            href=link,
                            target="_blank",
                            rel="noopener noreferrer",
                            class_="source-link",
                        ),
                        class_="source-headline",
                    ),
                    ui.tags.div(
                        f"{s.get('country', '')} · {s.get('section', '')} · {s.get('date', '')}",
                        class_="source-meta",
                    ),
                ]
                if trail:
                    src_children.append(ui.tags.p(trail, class_="source-trail"))
                blocks.append(ui.div(*src_children, class_="source-card"))
        meta = res.get("meta") or {}
        if meta:
            blocks.append(
                ui.tags.p(
                    f"Fetched {meta.get('articles_fetched', '—')} articles from the API; "
                    f"used the top {meta.get('sources_used', '—')} matches for context.",
                    class_="text-muted small px-3 pb-3 mb-0",
                )
            )
        return ui.div(*blocks)

# Status banner for errors and warnings
@render.ui
def status_banner():
    """Display error or warning messages from data fetching."""
    data = fetch_data()
    if not data:
        return ui.div()
    blocks = []
    if "error" in data:
        blocks.append(
            ui.tags.div(
                ui.tags.i(class_="fa-solid fa-circle-exclamation me-2"),
                data["error"],
                class_="alert alert-danger mb-3",
            )
        )
        return ui.div(*blocks)
    if "warning" in data:
        blocks.append(
            ui.tags.div(
                ui.tags.i(class_="fa-solid fa-triangle-exclamation me-2"),
                data["warning"],
                class_="alert alert-warning mb-3",
            )
        )
    if "rag_warning" in data:
        blocks.append(
            ui.tags.div(
                ui.tags.i(class_="fa-solid fa-circle-info me-2"),
                data["rag_warning"],
                class_="alert alert-info mb-3",
            )
        )
    return ui.div(*blocks) if blocks else ui.div()

# Row 1: Value boxes
with ui.layout_columns(col_widths=[4, 4, 4]):
    
    with ui.value_box(showcase=ui.tags.i(class_="fa-solid fa-newspaper"), theme="primary"):
        "Total Articles"
        
        @render.text
        def total_articles_vb():
            data = fetch_data()
            if not data or "error" in data:
                return "—"
            return f"{data['summary']['total_articles'].sum():,}"
    
    with ui.value_box(showcase=ui.tags.i(class_="fa-solid fa-globe"), theme="info"):
        "Countries Analyzed"
        
        @render.text
        def countries_count_vb():
            data = fetch_data()
            if not data or "error" in data:
                return "—"
            return str(len(data["summary"]))
    
    with ui.value_box(showcase=ui.tags.i(class_="fa-solid fa-trophy"), theme="success"):
        "Most Covered"
        
        @render.text
        def top_country_vb():
            data = fetch_data()
            if not data or "error" in data:
                return "—"
            return data["summary"].iloc[0]["country"]


# Row 2: Charts (Article Count + Per Capita)
with ui.layout_columns(col_widths=[6, 6]):
    
    with ui.card():
        ui.card_header("Article Count by Country")
        
        @render.ui
        def article_count_chart():
            data = fetch_data()
            if not data:
                return ui.p("Click 'Fetch Data' to load results.", class_="text-muted p-4")
            if "error" in data:
                return ui.p(data["error"], class_="text-danger p-4")
            
            df = data["summary"].sort_values("total_articles", ascending=True)
            fig = px.bar(
                df, x="total_articles", y="country",
                orientation="h",
                labels={"total_articles": "Total Articles", "country": ""},
                color="total_articles",
                color_continuous_scale=[[0, "#E8F0FE"], [1, "#007AFF"]],
            )
            fig.update_layout(
                margin=dict(l=0, r=20, t=10, b=0),
                showlegend=False,
                coloraxis_showscale=False,
                height=300,
                font=dict(family="Inter, -apple-system, sans-serif", color="#1D1D1F"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    
    with ui.card():
        ui.card_header("Coverage Per Capita (per 1M Population)")
        
        @render.ui
        def per_capita_chart():
            data = fetch_data()
            if not data:
                return ui.p("Click 'Fetch Data' to load results.", class_="text-muted p-4")
            if "error" in data:
                return ui.p(data["error"], class_="text-danger p-4")
            
            df = data["summary"].sort_values("articles_per_1m", ascending=True)
            fig = px.bar(
                df, x="articles_per_1m", y="country",
                orientation="h",
                labels={"articles_per_1m": "Articles per 1M People", "country": ""},
                color="articles_per_1m",
                color_continuous_scale=[[0, "#E8F8ED"], [1, "#34C759"]],
            )
            fig.update_layout(
                margin=dict(l=0, r=20, t=10, b=0),
                showlegend=False,
                coloraxis_showscale=False,
                height=300,
                font=dict(family="Inter, -apple-system, sans-serif", color="#1D1D1F"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))


# Row 3: Topic breakdown + Summary table
with ui.layout_columns(col_widths=[6, 6]):
    
    with ui.card():
        ui.card_header("Topic Breakdown by Country")
        
        @render.ui
        def topic_chart():
            data = fetch_data()
            if not data:
                return ui.p("Click 'Fetch Data' to load results.", class_="text-muted p-4")
            if "error" in data:
                return ui.p(data["error"], class_="text-danger p-4")
            
            df = data["articles"]
            topic_counts = df.groupby(["country", "topic"]).size().reset_index(name="count")
            topic_order = ["Politics", "Culture", "Crisis", "Sport", "Business", "Science", "Other"]
            
            fig = px.bar(
                topic_counts, x="count", y="country",
                color="topic",
                orientation="h",
                labels={"count": "Articles", "country": "", "topic": "Topic"},
                category_orders={"topic": topic_order},
                color_discrete_map=TOPIC_COLORS,
            )
            fig.update_layout(
                barmode="stack",
                margin=dict(l=0, r=20, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                height=300,
                font=dict(family="Inter, -apple-system, sans-serif", color="#1D1D1F"),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    
    with ui.card():
        ui.card_header("Country Coverage Summary")
        
        @render.data_frame
        def summary_table():
            data = fetch_data()
            if not data or "error" in data:
                return pd.DataFrame()
            
            display_df = data["summary"].rename(columns={
                "country": "Country",
                "total_articles": "Total Articles",
                "population_m": "Population (M)",
                "articles_per_1m": "Articles / 1M Pop",
            })
            return render.DataGrid(display_df, filters=True)


# Row 4: Pie chart + Sample articles
with ui.layout_columns(col_widths=[5, 7]):
    
    with ui.card():
        ui.card_header("Overall Topic Distribution")
        
        @render.ui
        def topic_pie():
            data = fetch_data()
            if not data:
                return ui.p("Click 'Fetch Data' to load results.", class_="text-muted p-4")
            if "error" in data:
                return ui.p(data["error"], class_="text-danger p-4")
            
            df = data["articles"]
            topic_totals = df["topic"].value_counts().reset_index()
            topic_totals.columns = ["topic", "count"]
            
            fig = px.pie(
                topic_totals, values="count", names="topic",
                color="topic",
                color_discrete_map=TOPIC_COLORS,
                hole=0.4,
            )
            fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300)
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    
    with ui.card():
        ui.card_header("Sample Articles")
        
        @render.data_frame
        def articles_table():
            data = fetch_data()
            if not data or "error" in data:
                return pd.DataFrame()
            
            display_df = data["articles"].filter(
                items=["country", "title", "topic", "section", "date"]
            ).rename(columns={
                "country": "Country",
                "title": "Title",
                "topic": "Topic",
                "section": "Section",
                "date": "Date",
            })
            return render.DataGrid(display_df, filters=True)


# Row 5: AI-Generated Analysis Report
with ui.card(full_screen=True):
    ui.card_header("AI-Generated Analysis Report")
    
    @render.ui
    def ai_report_card():
        # Check if AI button has been clicked
        if input.generate_ai() == 0:
            return ui.div(
                ui.p(
                    "Click 'Generate AI Report' in the sidebar to create an AI-powered analysis.",
                    class_="text-muted"
                ),
                class_="p-4"
            )
        
        report = generate_ai_report()
        
        # Render as markdown-style HTML
        return ui.div(
            ui.markdown(report),
            class_="p-3"
        )
