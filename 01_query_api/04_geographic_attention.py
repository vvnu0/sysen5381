# Analyze which countries receive the most news coverage
# Search for articles mentioning different countries and compare their coverage volume.

# =====================================================
# API Explaination
# =====================================================
# API Name: The Guardian Open Platform API
# Base URL: https://content.guardianapis.com
# Endpoint: /search
#
# Key Parameters Used:
#   - q: Search query term (we use country names)
#   - api-key: Your API key for authentication
#   - from-date: Filter articles published after this date (YYYY-MM-DD)
#   - to-date: Filter articles published before this date (YYYY-MM-DD)
#   - page-size: Number of results per page (max 200)
#   - show-fields: Request additional fields (headline, trailText, wordcount)
#
# Expected Output:
#   - status: "ok" if successful
#   - total: Total number of matching articles
#   - results: Array of article objects
# =====================================================

# 0. Setup
# packages
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

# api key
load_dotenv(".env")
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")

# error handling
if not GUARDIAN_API_KEY:
    print("ERROR: GUARDIAN_API_KEY not found in .env file")
    print("Please add: GUARDIAN_API_KEY=your_key_here")
    exit(1)

# query parameters - countries to analyze
countries = [
    "United States",
    "United Kingdom",
    "China",
    "India",
    "Russia",
    "Brazil",
    "Germany",
    "France",
    "Australia",
    "Japan"
]

# date range is last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)
from_date_str = start_date.strftime("%Y-%m-%d")
to_date_str = end_date.strftime("%Y-%m-%d")

# 1. API Query
results_list = []

print(f"Querying Guardian API for articles from {from_date_str} to {to_date_str}")
print(f"Searching for coverage of {len(countries)} countries...\n")

# repeat for each country & get article counts
for country in countries:
    response = requests.get(
        "https://content.guardianapis.com/search",
        params={
            "q": country,                    # Search for country name
            "from-date": from_date_str,      # Start of date range
            "to-date": to_date_str,          # End of date range
            "page-size": 5,                  # Get 5 sample articles
            "show-fields": "headline,trailText,wordcount",  # Extra fields
            "api-key": GUARDIAN_API_KEY
        }
    )
    
    # error handling
    if response.status_code != 200:
        print(f"  ERROR: {country} - Status code {response.status_code}")
        continue
    

    data = response.json()
    if data.get("response", {}).get("status") != "ok":
        print(f"  ERROR: {country} - API returned error")
        continue
    
    # get the key & store summary for this country
    total_articles = data["response"]["total"]
    articles = data["response"]["results"]
    country_result = {
        "country": country,
        "total_articles": total_articles,
        "sample_count": len(articles),
        "date_range": f"{from_date_str} to {to_date_str}"
    }
    results_list.append(country_result)
    
    # detailed view for the future
    for article in articles:
        article_data = {
            "country_query": country,
            "title": article.get("webTitle", "N/A"),
            "section": article.get("sectionName", "N/A"),
            "date": article.get("webPublicationDate", "N/A")[:10],
            "url": article.get("webUrl", "N/A")
        }

# 2. Display

print("=" * 60)
print("GEOGRAPHIC ATTENTION MAP - RESULTS SUMMARY")
print("=" * 60)

#record count

print(f"\nTotal Records: {len(results_list)} countries analyzed")
print(f"Date Range: {from_date_str} to {to_date_str}")

print("\n--- Data Structure ---")
print("Each record contains:")
print("  - country: Name of the country searched")
print("  - total_articles: Total Guardian articles mentioning this country")
print("  - sample_count: Number of sample articles retrieved")
print("  - date_range: The date range of the search")

#key fields

print("\n--- Coverage by Country (Last 30 Days) ---")
print(f"{'Country':<20} {'Total Articles':>15}")
print("-" * 37)

# sort & print most covered countries
sorted_results = sorted(results_list, key=lambda x: x["total_articles"], reverse=True)

for result in sorted_results:
    print(f"{result['country']:<20} {result['total_articles']:>15,}")

# sample raw data
print("\n--- Sample Raw Data (First 3 Records) ---")
for i, result in enumerate(sorted_results[:3]):
    print(f"\nRecord {i + 1}:")
    print(f"  country: '{result['country']}'")
    print(f"  total_articles: {result['total_articles']}")
    print(f"  sample_count: {result['sample_count']}")
    print(f"  date_range: '{result['date_range']}'")

# summary stats
total_coverage = sum(r["total_articles"] for r in results_list)
avg_coverage = total_coverage / len(results_list) if results_list else 0
top_country = sorted_results[0]["country"] if sorted_results else "N/A"

print("\n--- Summary Statistics ---")
print(f"Total articles across all countries: {total_coverage:,}")
print(f"Average articles per country: {avg_coverage:,.1f}")
print(f"Most covered country: {top_country}")

print("\n" + "=" * 60)
print("Query completed successfully!")
print("=" * 60)
