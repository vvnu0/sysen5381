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

## 0.2 Load Environment Variables ################

# Load .env from project root (three levels up from this app)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")

## 0.3 Ollama Configuration ######################

OLLAMA_PORT = 11434
OLLAMA_URL = f"http://localhost:{OLLAMA_PORT}/api/generate"
OLLAMA_MODEL = "gemma3:latest"

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
    "Politics": "#636EFA", "Culture": "#EF553B", "Crisis": "#FFA15A",
    "Sport": "#00CC96", "Business": "#AB63FA", "Science": "#19D3F3",
    "Other": "#B6B6B6",
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
    """Send data to Ollama and return AI-generated analysis."""
    
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
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        
        if response.status_code != 200:
            return f"Error: Ollama returned status {response.status_code}. Make sure Ollama is running."
        
        result = response.json()
        if "response" not in result:
            return "Error: Unexpected response format from Ollama."
        
        return result["response"]
    
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to Ollama. Make sure it is running with `ollama serve`."
    except Exception as e:
        return f"Error: {str(e)}"


# 2. Page Configuration ############################

# Set page title (compatible with older Shiny versions)
ui.tags.title("Geographic Attention Reporter")

# 3. Sidebar — Input Controls ######################

with ui.sidebar(open="desktop", width=320):
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

# Status banner for errors and warnings
@render.ui
def status_banner():
    """Display error or warning messages from data fetching."""
    data = fetch_data()
    if not data:
        return ui.div()
    if "error" in data:
        return ui.div(
            ui.tags.div(
                ui.tags.i(class_="fa-solid fa-circle-exclamation me-2"),
                data["error"],
                class_="alert alert-danger mb-3",
            )
        )
    if "warning" in data:
        return ui.div(
            ui.tags.div(
                ui.tags.i(class_="fa-solid fa-triangle-exclamation me-2"),
                data["warning"],
                class_="alert alert-warning mb-3",
            )
        )
    return ui.div()

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
                color_continuous_scale="Blues",
            )
            fig.update_layout(
                margin=dict(l=0, r=20, t=10, b=0),
                showlegend=False,
                coloraxis_showscale=False,
                height=300,
            )
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))
    
    with ui.card():
        ui.card_header("Coverage Per Capita (Articles per 1M Population)")
        
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
                color_continuous_scale="Greens",
            )
            fig.update_layout(
                margin=dict(l=0, r=20, t=10, b=0),
                showlegend=False,
                coloraxis_showscale=False,
                height=300,
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
                ui.p(
                    "Requirements: Ollama must be running locally with the gemma3 model.",
                    class_="text-muted small"
                ),
                class_="p-4"
            )
        
        report = generate_ai_report()
        
        # Render as markdown-style HTML
        return ui.div(
            ui.markdown(report),
            class_="p-3"
        )
