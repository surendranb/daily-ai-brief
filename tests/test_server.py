"""Native unit tests for daily-ai-brief MCP server tools."""

import pytest
from daily_ai_brief.server import (
    get_arxiv_breakthroughs,
    get_daily_ai_brief,
    get_frontier_lab_updates,
    get_ai_podcasts,
    get_model_drops,
    skill_read,
    skills_list,
)


def test_get_daily_ai_brief():
    brief = get_daily_ai_brief(focus_areas=["frontier_labs", "papers"])
    assert "# 🌅 Daily AI Intelligence Brief" in brief
    assert "Frontier Lab Announcements" in brief
    assert "Preprints & Research" in brief


def test_get_frontier_lab_updates():
    res = get_frontier_lab_updates(labs=["deepmind"], max_items=2)
    assert isinstance(res, str)
    assert len(res) > 0


def test_get_ai_podcasts():
    res = get_ai_podcasts(podcasts=["latent_space"], max_items=1)
    assert isinstance(res, str)
    assert len(res) > 0


def test_get_model_drops():
    res = get_model_drops(limit=3)
    assert "Trending Open-Weight Models" in res
    assert "Model ID" in res


def test_skills_tools():
    s_list = skills_list()
    assert "ai_brief_skill" in s_list

    s_read = skill_read("ai_brief_skill")
    assert "Daily AI Brief Playbook" in s_read


def test_intent_parameter_support():
    brief = get_daily_ai_brief(focus_areas=["frontier_labs"], intent="Check frontier lab releases")
    assert "# 🌅 Daily AI Intelligence Brief" in brief

