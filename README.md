# AI Project

An AI-powered application with agent-based architecture for natural language query processing.

## Project Structure

```
app/
├── main.py                 # Application entry point
├── core/                   # Core configuration
├── api/                    # API routes
├── agents/                 # AI agents
├── prompts/                # Prompt templates
├── db/                     # Database connections
└── utils/                  # Utility functions

tests/                      # Test suite
```

## Setup

1. Copy `.env.example` to `.env` and fill in your configuration:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app/main.py
   ```

## Agents

- **User Query Validator**: Validates incoming user queries
- **MongoDB Query Builder**: Converts natural language to MongoDB queries
- **Result Summarizer**: Summarizes query results
- **Suggested Questions**: Generates follow-up questions

## Testing

```bash
pytest tests/
```

## License

MIT
