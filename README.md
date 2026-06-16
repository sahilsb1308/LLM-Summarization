# MoveUp Content Ops Bot

An AI-powered YouTube performance analytics platform for MoveUp Media. Automatically collects metrics from YouTube channels, generates structured LLM reports, and provides a conversational agent for ad-hoc analysis.

## Features

- **Automated data collection** — fetches last 10 videos from Netflu and ThePlayoffsTV via YouTube Data API v3
- **AI-generated reports** — Claude analyzes the data and produces structured performance reports with per-video ratings, top/bottom performers, and actionable recommendations
- **Management dashboard** — Streamlit UI with KPI cards, color-coded video tables, and competitive benchmarks
- **Conversational agent** — autonomous Claude agent with tool use for natural language queries ("Which video dropped the most?", "Compare us to BeFootball")
- **Competitive benchmark** — includes BeFootball and Oh My Goal as competitor channels in the same sports/entertainment content sector
- **Weekly auto-refresh** — APScheduler regenerates the report every Monday at 08:00 UTC automatically

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Language | Python 3.11+ | Ecosystem for data + AI |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) | Best instruction-following, tool use, structured output |
| Data | YouTube Data API v3 | Official, free, sufficient quota |
| UI | Streamlit | Fastest path to a production-quality management interface |
| Scheduling | APScheduler | Lightweight in-process scheduler, no infra needed |

## Setup (under 10 minutes)

### 1. Clone and install
```bash
git clone <your-repo-url>
cd moveup-content-ops
pip install -r requirements.txt
```

### 2. Configure API keys
```bash
cp .env.example .env
```

Edit `.env`:
```
YOUTUBE_API_KEY=your_key   # Google Cloud Console → Enable YouTube Data API v3
ANTHROPIC_API_KEY=your_key # console.anthropic.com
```

**YouTube API key**: Google Cloud Console → Create project → APIs & Services → Enable "YouTube Data API v3" → Credentials → Create API Key. Takes ~5 minutes.

### 3. Run
```bash
streamlit run app.py
```

Open http://localhost:8501

## Usage

1. **Settings** → "Collect Fresh Data" - fetches YouTube metrics for all channels
2. **Settings** → "Generate AI Report" - runs Claude analysis on collected data
3. **Performance Report** - view the full AI-generated report
4. **Dashboard** - visual KPIs and color-coded video tables
5. **Conversational Agent** - ask natural language questions; agent calls YouTube API live

## Competitive Channels Rationale

| Channel | Reason |
|---|---|
| **BeFootball** | Large European football content channel, directly comparable to ThePlayoffsTV's sports content |
| **Oh My Goal** | Global football highlights channel with similar audience demographics to Netflu |

Both channels operate in the same sports entertainment content vertical as MoveUp Media, making them meaningful benchmarks for engagement rates and content strategy.

## Project Structure

```
├── app.py              # Streamlit UI (Dashboard, Report, Agent, Settings)
├── src/
│   ├── youtube.py      # YouTube Data API v3 fetcher + channel config
│   ├── analyzer.py     # LLM report generator with engineered prompts
│   ├── agent.py        # Autonomous conversational agent with tool use
│   └── scheduler.py    # Weekly APScheduler background job
├── data/reports/       # Cached data (JSON) and reports (Markdown)
├── requirements.txt
└── .env.example
```
