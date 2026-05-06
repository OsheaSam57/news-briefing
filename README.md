# news-briefing

Personal AI-powered news briefing pipeline that ingests RSS feeds, scores them with Anthropic, summarises qualifying stories, and renders a daily HTML digest.

## What it does

- Pulls RSS stories across AI/ML, Data Science, Insurance/Actuarial, and Economics/Markets
- Stores raw article metadata in SQLite with URL deduplication
- Uses Anthropic to score relevance from 1 to 10 and keeps the top 3 articles per source
- Summarises qualifying articles and adds an automotive protection / GAP insurance callout for Economics/Markets stories
- Renders the final digest to `output/digest.html`
- Includes a daily GitHub Actions schedule at `07:00 UTC`

## First run

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

3. Run the pipeline:

```bash
python main.py
```

If the run succeeds, the digest will be written to `output/digest.html` and the SQLite database will be created at `data/news_briefing.db`.

## GitHub Actions

Add `ANTHROPIC_API_KEY` as a repository secret before enabling the scheduled workflow.
