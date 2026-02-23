# app.py
# Guardian Geographic Attention Dashboard
# A Shiny for Python app showing global news coverage patterns
# Built for DSAI 02_productivity lab

# This app queries The Guardian API for articles mentioning different
# countries, then visualizes coverage volume, topic breakdown, and
# per-capita coverage in an interactive dashboard.

# 0. Setup #################################

## 0.1 Load Packages ############################

import os                          # for file paths and env vars
from pathlib import Path           # for resolving .env location
from datetime import datetime, timedelta  # for date calculations

import pandas as pd                # for data manipulation
import requests                    # for making HTTP requests
from dotenv import load_dotenv     # for loading .env variables

import plotly.express as px        # for interactive charts
import plotly.graph_objects as go  # for advanced plotly figures

from shiny import reactive, render, ui  # shiny core
from shiny.express import input, ui     # shiny express helpers

## 0.2 Load Environment Variables ################

# The .env file lives in the project root (two levels up from this app)
# We resolve the path so the app works regardless of working directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")

## 0.3 Constants #################################

# Countries to analyze — same list as 04_geographic_attention.py
COUNTRIES = [
    "United States", "United Kingdom", "China", "India", "Russia",
    "Brazil", "Germany", "France", "Australia", "Japan",
]

# Approximate 2024 populations in millions (for per-capita calculation)
POPULATIONS = {
    "United States": 334,
    "United Kingdom": 68,
    "China": 1425,
    "India": 1438,
    "Russia": 144,
    "Brazil": 216,
    "Germany": 84,
    "France": 68,
    "Australia": 26,
    "Japan": 124,
}

# Map Guardian sectionId values to broad topic categories
# This lets us group dozens of sections into a handful of themes
TOPIC_MAP = {
    # Politics & Government
    "politics": "Politics",
    "world": "Politics",
    "us-news": "Politics",
    "uk-news": "Politics",
    "australia-news": "Politics",
    "law": "Politics",
    "global": "Politics",
    # Culture & Entertainment
    "culture": "Culture",
    "music": "Culture",
    "film": "Culture",
    "books": "Culture",
    "artanddesign": "Culture",
    "stage": "Culture",
    "tv-and-radio": "Culture",
    "games": "Culture",
    "food": "Culture",
    # Crisis & Global Issues
    "environment": "Crisis",
    "global-development": "Crisis",
    "society": "Crisis",
    "inequality": "Crisis",
    # Sport
    "sport": "Sport",
    "football": "Sport",
    "cricket": "Sport",
    "rugby-union": "Sport",
    "tennis": "Sport",
    "cycling": "Sport",
    "formulaone": "Sport",
    # Business & Tech
    "business": "Business",
    "technology": "Business",
    "money": "Business",
    "media": "Business",
    # Science & Health
    "science": "Science",
    "lifeandstyle": "Science",
    "education": "Science",
}

# Consistent color palette for topics
TOPIC_COLORS = {
    "Politics": "#636EFA",
    "Culture": "#EF553B",
    "Crisis": "#FFA15A",
    "Sport": "#00CC96",
    "Business": "#AB63FA",
    "Science": "#19D3F3",
    "Other": "#B6B6B6",
}


# 1. Helper Functions ##############################

def classify_topic(section_id):
    """Classify a Guardian sectionId into a broad topic category."""
    return TOPIC_MAP.get(section_id.lower(), "Other") if section_id else "Other"


def query_guardian(country, from_date, to_date, api_key):
    """
    Query the Guardian API for articles mentioning a country.
    Returns a list of article dicts with country, title, section, topic, date.
    """
    try:
        response = requests.get(
            "https://content.guardianapis.com/search",
            params={
                "q": country,
                "from-date": from_date,
                "to-date": to_date,
                "page-size": 50,          # get up to 50 articles per country
                "show-fields": "headline,trailText,wordcount",
                "api-key": api_key,
            },
            timeout=15,
        )

        # Check for HTTP errors
        if response.status_code != 200:
            return [], 0

        data = response.json()
        resp = data.get("response", {})

        if resp.get("status") != "ok":
            return [], 0

        total = resp.get("total", 0)
        articles = []

        for article in resp.get("results", []):
            section_id = article.get("sectionId", "")
            articles.append({
                "country": country,
                "title": article.get("webTitle", "N/A"),
                "section": article.get("sectionName", "N/A"),
                "section_id": section_id,
                "topic": classify_topic(section_id),
                "date": article.get("webPublicationDate", "")[:10],
                "url": article.get("webUrl", ""),
            })

        return articles, total

    except Exception:
        return [], 0


# 2. Page Configuration ############################

# Set the page title and make the layout fillable for a modern look
ui.page_opts(
    title="Guardian Geographic Attention Dashboard",
    fillable=True,
)

# 3. Sidebar — Input Controls ######################

with ui.sidebar(open="desktop", width=300):
    ui.h4("Query Parameters")
    ui.hr()

    # Date range inputs — default to last 30 days
    ui.input_date(
        "from_date", "From Date",
        value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
    )
    ui.input_date(
        "to_date", "To Date",
        value=datetime.now().strftime("%Y-%m-%d"),
    )

    ui.hr()

    # Country selection — all selected by default
    ui.input_checkbox_group(
        "countries", "Countries to Analyze",
        choices=COUNTRIES,
        selected=COUNTRIES,
    )

    ui.hr()

    # Action button — triggers the API query on click
    ui.input_action_button(
        "run_query", "Fetch Data", class_="btn-primary w-100",
    )

    ui.hr()
    ui.markdown(
        "*Data source: [The Guardian Open Platform]"
        "(https://open-platform.theguardian.com/)*"
    )

# 4. Reactive Data — Fetch & Process ###############

@reactive.calc
@reactive.event(input.run_query)
def fetch_data():
    """
    When the user clicks 'Fetch Data', query the Guardian API
    for each selected country and return a combined DataFrame.
    """
    # Check for API key
    if not GUARDIAN_API_KEY:
        return pd.DataFrame()

    selected = list(input.countries())
    if not selected:
        return pd.DataFrame()

    from_date = str(input.from_date())
    to_date = str(input.to_date())

    all_articles = []
    totals = {}

    # Query each country
    for country in selected:
        articles, total = query_guardian(country, from_date, to_date, GUARDIAN_API_KEY)
        all_articles.extend(articles)
        totals[country] = total

    if not all_articles:
        return pd.DataFrame()

    # Build the articles DataFrame
    df = pd.DataFrame(all_articles)

    # Build a summary DataFrame with total counts and population data
    summary = (pd.DataFrame(
            [{"country": c, "total_articles": totals.get(c, 0)} for c in selected]
        )
        .assign(
            population_m=lambda x: x["country"].map(POPULATIONS),
            articles_per_1m=lambda x: (
                x["total_articles"] / x["population_m"]
            ).round(1),
        )
        .sort_values("total_articles", ascending=False)
    )

    return {"articles": df, "summary": summary}


# 5. Main Panel — Dashboard Layout #################

# Show a warning if API key is missing
if not GUARDIAN_API_KEY:
    ui.notification_show(
        "GUARDIAN_API_KEY not found in .env file. "
        "Please add it and restart the app.",
        type="error",
        duration=None,
    )

# Row of value boxes at the top
with ui.layout_columns(col_widths=[4, 4, 4]):

    with ui.value_box(showcase=ui.tags.i(class_="fa-solid fa-newspaper"), theme="primary"):
        "Total Articles"

        @render.text
        def total_articles_vb():
            data = fetch_data()
            if not data or "summary" not in data:
                return "—"
            return f"{data['summary']['total_articles'].sum():,}"

    with ui.value_box(showcase=ui.tags.i(class_="fa-solid fa-globe"), theme="info"):
        "Countries Analyzed"

        @render.text
        def countries_count_vb():
            data = fetch_data()
            if not data or "summary" not in data:
                return "—"
            return str(len(data["summary"]))

    with ui.value_box(showcase=ui.tags.i(class_="fa-solid fa-trophy"), theme="success"):
        "Most Covered"

        @render.text
        def top_country_vb():
            data = fetch_data()
            if not data or "summary" not in data:
                return "—"
            return data["summary"].iloc[0]["country"]


# Charts row 1 — Article counts and Per-capita coverage
with ui.layout_columns(col_widths=[6, 6]):

    # Card 1: Article count by country
    with ui.card():
        ui.card_header("Article Count by Country")

        @render.ui
        def article_count_chart():
            data = fetch_data()
            if not data or "summary" not in data:
                return ui.p("Click 'Fetch Data' to load results.", class_="text-muted p-4")

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
                height=350,
            )
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Card 2: Coverage per capita
    with ui.card():
        ui.card_header("Coverage Per Capita (Articles per 1M Population)")

        @render.ui
        def per_capita_chart():
            data = fetch_data()
            if not data or "summary" not in data:
                return ui.p("Click 'Fetch Data' to load results.", class_="text-muted p-4")

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
                height=350,
            )
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))


# Charts row 2 — Topic breakdown and data table
with ui.layout_columns(col_widths=[6, 6]):

    # Card 3: Topic breakdown per country (stacked bar)
    with ui.card():
        ui.card_header("Topic Breakdown by Country")

        @render.ui
        def topic_chart():
            data = fetch_data()
            if not data or "articles" not in data:
                return ui.p("Click 'Fetch Data' to load results.", class_="text-muted p-4")

            df = data["articles"]

            # Count articles by country and topic
            topic_counts = (df
                .groupby(["country", "topic"])
                .size()
                .reset_index(name="count")
            )

            # Ensure consistent topic ordering
            topic_order = ["Politics", "Culture", "Crisis", "Sport", "Business", "Science", "Other"]

            fig = px.bar(
                topic_counts, x="count", y="country",
                color="topic",
                orientation="h",
                labels={"count": "Articles (sampled)", "country": "", "topic": "Topic"},
                category_orders={"topic": topic_order},
                color_discrete_map=TOPIC_COLORS,
            )
            fig.update_layout(
                barmode="stack",
                margin=dict(l=0, r=20, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                height=350,
            )
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Card 4: Summary data table
    with ui.card():
        ui.card_header("Country Coverage Summary")

        @render.data_frame
        def summary_table():
            data = fetch_data()
            if not data or "summary" not in data:
                return pd.DataFrame()

            display_df = (data["summary"]
                .rename(columns={
                    "country": "Country",
                    "total_articles": "Total Articles",
                    "population_m": "Population (M)",
                    "articles_per_1m": "Articles / 1M Pop",
                })
            )
            return render.DataGrid(display_df, filters=True)


# Bottom row — Topic distribution pie chart and article sample
with ui.layout_columns(col_widths=[5, 7]):

    # Card 5: Overall topic distribution (pie chart)
    with ui.card():
        ui.card_header("Overall Topic Distribution")

        @render.ui
        def topic_pie():
            data = fetch_data()
            if not data or "articles" not in data:
                return ui.p("Click 'Fetch Data' to load results.", class_="text-muted p-4")

            df = data["articles"]
            topic_totals = df["topic"].value_counts().reset_index()
            topic_totals.columns = ["topic", "count"]

            fig = px.pie(
                topic_totals, values="count", names="topic",
                color="topic",
                color_discrete_map=TOPIC_COLORS,
                hole=0.4,  # donut chart for modern look
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                height=350,
            )
            return ui.HTML(fig.to_html(full_html=False, include_plotlyjs="cdn"))

    # Card 6: Sample articles table
    with ui.card():
        ui.card_header("Sample Articles")

        @render.data_frame
        def articles_table():
            data = fetch_data()
            if not data or "articles" not in data:
                return pd.DataFrame()

            display_df = (data["articles"]
                .filter(items=["country", "title", "topic", "section", "date"])
                .rename(columns={
                    "country": "Country",
                    "title": "Title",
                    "topic": "Topic",
                    "section": "Section",
                    "date": "Date",
                })
            )
            return render.DataGrid(display_df, filters=True)
