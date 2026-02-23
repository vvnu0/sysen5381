# Geographic Attention Reporter

An integrated AI-powered Shiny application that analyzes global news coverage patterns using The Guardian API and generates insights with Ollama.

## Features

This application demonstrates three core capabilities:

| Lab | Feature | Description |
|-----|---------|-------------|
| LAB 1 | API Integration | Queries The Guardian API for articles mentioning 10 countries |
| LAB 2 | Shiny Dashboard | Interactive charts, tables, and value boxes |
| LAB 3 | AI Reporting | Generates analytical insights using Ollama LLM |

## Dashboard Components

- **Value Boxes**: Total articles, countries analyzed, most covered country
- **Bar Charts**: Article count by country, per-capita coverage
- **Topic Analysis**: Stacked bar chart and pie chart showing topic distribution
- **Data Tables**: Filterable summary and article tables
- **AI Report**: Generated analysis with statistics, insights, and implications

---

## Data Summary

### Article Data (from Guardian API)

| Column | Data Type | Description |
|--------|-----------|-------------|
| `country` | string | Country name used in the search query |
| `title` | string | Article headline (`webTitle` from API) |
| `section` | string | Guardian section name (e.g., "World news", "Sport") |
| `section_id` | string | Section identifier used for topic classification |
| `topic` | string | Derived category: Politics, Culture, Crisis, Sport, Business, Science, Other |
| `pillar` | string | Guardian pillar classification (News, Opinion, Sport, Arts, Lifestyle) |
| `wordcount` | integer | Article word count (from `fields.wordcount`) |
| `date` | string | Publication date in YYYY-MM-DD format |
| `url` | string | Full URL to the article on The Guardian website |

### Summary Data (computed)

| Column | Data Type | Description |
|--------|-----------|-------------|
| `country` | string | Country name |
| `total_articles` | integer | Total number of articles mentioning the country |
| `population_m` | float | Country population in millions (hardcoded reference data) |
| `articles_per_1m` | float | Articles per million population (coverage intensity metric) |

---

## Technical Details

### API Configuration

| Setting | Value |
|---------|-------|
| **API Provider** | The Guardian Open Platform |
| **Base URL** | `https://content.guardianapis.com/search` |
| **Authentication** | API key passed as `api-key` query parameter |
| **Rate Limit** | 12 requests/second, 5,000 requests/day (free tier) |

### API Query Parameters



| Parameter | Value | Purpose |
|-----------|-------|---------|
| `q` | Country name | Search term |
| `from-date` | YYYY-MM-DD | Start of date range |
| `to-date` | YYYY-MM-DD | End of date range |
| `page-size` | 50 | Maximum articles per request |
| `show-fields` | wordcount | Additional fields to retrieve |
| `api-key` | From .env | Authentication |

### Ollama Configuration

| Setting | Value |
|---------|-------|
| **Host** | `http://localhost:11434` |
| **Endpoint** | `/api/generate` |
| **Model** | `gemma3:latest` |
| **Timeout** | 120 seconds |

### File Structure

```
dsai/
├── .env                        # API keys (GUARDIAN_API_KEY)
└── 04_deployment/
    └── app/
        ├── app.py              # Main Shiny application (694 lines)
        ├── requirements.txt    # Python dependencies
        └── README.md           # This documentation
```

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `shiny` | latest | Web application framework |
| `pandas` | latest | Data manipulation and aggregation |
| `plotly` | latest | Interactive chart visualizations |
| `requests` | latest | HTTP requests to APIs |
| `python-dotenv` | latest | Load environment variables from .env |
| `python-dateutil` | latest | Date calculations (relativedelta) |

---

## Usage Instructions

### Prerequisites

1. **Python 3.9+** with pip
2. **Guardian API Key**: Register free at [The Guardian Open Platform](https://open-platform.theguardian.com/access/)
3. **Ollama** (optional, for AI features): Install from [ollama.ai](https://ollama.ai/)

### Step 1: Install Dependencies

```bash
cd 04_deployment/app
pip install -r requirements.txt
```

### Step 2: Configure API Key

Create a `.env` file in the project root (`dsai/.env`):

```
GUARDIAN_API_KEY=your_api_key_here
```

To get an API key:
1. Go to [open-platform.theguardian.com/access](https://open-platform.theguardian.com/access/)
2. Click "Register for a developer key"
3. Fill out the form and submit
4. Copy the key from your confirmation email

### Step 3: Start Ollama (for AI features)

```bash
# Pull the model (first time only, ~2GB download)
ollama pull gemma3:latest

# Start the Ollama server (keep this running)
ollama serve
```

### Step 4: Run the Application

```bash
cd 04_deployment/app
shiny run app.py
```

Open your browser to `http://localhost:8000`.

### Step 5: Using the Dashboard

1. **Set Date Range**: Adjust "From Date" and "To Date" in the sidebar
2. **Select Countries**: Check/uncheck countries to analyze (default: all 10)
3. **Fetch Data**: Click the "Fetch Data" button to query the API
4. **Explore Visualizations**: View charts and tables that update automatically
5. **Generate AI Report**: Click "Generate AI Report" for LLM-powered analysis

---

## AI Prompt Design

The AI analysis uses a carefully crafted prompt:

| Element | Description |
|---------|-------------|
| **Role** | Media analyst specializing in global news coverage |
| **Chain-of-Thought** | 6-step reasoning: coverage volume → per-capita → depth → tone → factors → conclusions |
| **Constraints** | Formal language, no hyperbole, specific numbers/percentages |
| **Output** | Key Statistics (3-4 bullets), 2 Deep Insights, Implications |

---

## Error Handling

The application handles errors gracefully:

| Error Type | Handling |
|------------|----------|
| Missing API key | Red alert banner, disabled queries |
| Invalid API key | Error message with 401 status |
| Rate limit exceeded | Error message with 429 status |
| Network timeout | 15-second timeout with retry suggestion |
| Partial failures | Yellow warning banner showing which countries failed |
| Ollama not running | Friendly error with instructions |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "GUARDIAN_API_KEY not found" | Create `.env` file in `dsai/` folder with your key |
| "Could not connect to Ollama" | Run `ollama serve` in a separate terminal |
| "Model not found" | Run `ollama pull gemma3:latest` |
| Charts don't load | Click "Fetch Data" button after selecting countries |
| Partial data only | Check warning banner for which countries failed |
| Slow AI response | Ollama may take 30-60 seconds on first generation |

---

## Data Sources

- **News Data**: [The Guardian Open Platform API](https://open-platform.theguardian.com/)
- **Population Data**: Approximate 2024 figures (Wikipedia) for per-capita calculations
