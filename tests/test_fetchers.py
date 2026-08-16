"""Unit tests for daily-ai-brief fetchers."""

import pytest
from daily_ai_brief.fetchers.community import (
    fetch_github_trending_ai,
    fetch_hf_trending_models,
    fetch_hn_ai_pulse,
)
from daily_ai_brief.fetchers.frontier_labs import (
    fetch_all_frontier_labs,
    fetch_lab_feed,
)
from daily_ai_brief.fetchers.papers import (
    fetch_arxiv_breakthroughs,
    fetch_hf_daily_papers,
)
from daily_ai_brief.fetchers.podcasts import (
    fetch_all_ai_podcasts,
    fetch_podcast_episodes,
)


def test_frontier_labs_fetcher():
    items = fetch_all_frontier_labs(labs=["deepmind", "bair"], max_per_lab=2)
    assert isinstance(items, list)
    if items:
        assert "lab" in items[0]
        assert "title" in items[0]
        assert "link" in items[0]


def test_hf_daily_papers_fetcher():
    papers = fetch_hf_daily_papers(max_papers=3)
    assert isinstance(papers, list)
    if papers:
        assert "title" in papers[0]
        assert "url" in papers[0]


def test_arxiv_fetcher():
    results = fetch_arxiv_breakthroughs(categories=["cs.AI"], max_results=3)
    assert isinstance(results, list)
    if results:
        assert "title" in results[0]
        assert "url" in results[0]


def test_podcasts_fetcher():
    episodes = fetch_all_ai_podcasts(podcasts=["latent_space"], max_per_show=2)
    assert isinstance(episodes, list)
    if episodes:
        assert "podcast" in episodes[0]
        assert "title" in episodes[0]


def test_community_signals():
    models = fetch_hf_trending_models(limit=3)
    assert isinstance(models, list)

    hn = fetch_hn_ai_pulse(min_points=20, limit=3)
    assert isinstance(hn, list)
