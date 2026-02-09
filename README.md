# Procurement AI Assistant (Backend)

Multi-agent AI system that converts natural language questions into MongoDB queries for California state procurement data (FY 2012–2015). Returns structured JSON with answers, data, and suggested follow-up questions.

## Quick Start

```bash
cp .env.example .env  # Add OpenAI key and MongoDB URI
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/ingest_csv_to_mongo.py  # Load 346,018 records
uvicorn app.main:app --reload
```

API runs at `http://localhost:8000`. Hit `/api/chat` with user messages.

## What it does

- Validates user questions and asks for clarification if needed
- Converts natural language → MongoDB aggregation pipelines
- Self-validates and refines queries for accuracy
- Generates natural language summaries from results
- Suggests 3 contextual follow-up questions
- Returns structured data with column metadata for visualization

## How it works

Five specialized LLM agents orchestrated in sequence:
1. **User Query Validator** – Normalizes questions or requests clarification
2. **Mongo Query Builder** – Generates aggregation pipelines from natural language
3. **Mongo Query Validator** – Checks result quality and suggests refinements (max 1 iteration)
4. **Result Summarizer** – Creates conversational answers from data
5. **Suggested Questions** – Generates contextual follow-ups

Each agent uses structured prompts and returns typed Pydantic schemas for reliability.

## Stack

- FastAPI for REST API
- LangChain for agentic framework
- OpenAI GPT-5.1 for agents
- MongoDB for data storage
- Pydantic for schema validation
- Python 3.11+

---

**Data**: 346,018 California state procurement records with fiscal/calendar year fields for filtering.

**Source**: Dataset downloaded from [Kaggle - Large Purchases by the State of CA](https://www.kaggle.com/datasets/sohier/large-purchases-by-the-state-of-ca). The CSV file (`data/procurement.csv`) is in `.gitignore` due to its size. Download from Kaggle if setting up a new environment.

**Field Catalog**: `app/core/field_catalog.json` was generated separately based on data documentation and designed alongside the CSV ingestion script to provide field metadata (types, descriptions, synonyms) for the query builder agent.
