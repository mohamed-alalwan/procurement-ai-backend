"""Smoke tests for agents."""

import pytest


def test_agents_import():
    """Test that agents can be imported."""
    from app.agents import orchestrator
    from app.agents import user_query_validator
    from app.agents import mongo_query_builder
    from app.agents import result_summarizer
    from app.agents import suggested_questions
    
    assert orchestrator is not None
    assert user_query_validator is not None
    assert mongo_query_builder is not None
    assert result_summarizer is not None
    assert suggested_questions is not None
