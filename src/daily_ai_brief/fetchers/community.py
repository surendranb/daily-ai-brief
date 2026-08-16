"""Community Consensus & Ecosystem Signals Fetcher.
Zero-auth ingestion for Hugging Face Hub Trending Models, GitHub Trending AI repos, and Hacker News AI Pulse.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


USER_AGENT = "daily-ai-brief/0.1.0 (https://github.com/surendranb/daily-ai-brief; ai-ecosystem-bot)"


def fetch_hf_trending_models(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch trending and top downloaded new models on Hugging Face Hub."""
    url = f"https://huggingface.co/api/models?sort=likes7d&direction=-1&limit={limit}&full=false"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        models = []
        for m in data:
            model_id = m.get("id", "")
            likes = m.get("likes", 0)
            downloads = m.get("downloads", 0)
            tags = m.get("tags", [])
            pipeline_tag = m.get("pipeline_tag", "unknown")

            models.append({
                "model_id": model_id,
                "pipeline_tag": pipeline_tag,
                "likes": likes,
                "downloads": downloads,
                "tags": [t for t in tags if not t.startswith("license:")][:5],
                "url": f"https://huggingface.co/{model_id}",
            })
        return models
    except Exception:
        # Fallback to sort=downloads
        try:
            fallback_url = f"https://huggingface.co/api/models?sort=downloads&direction=-1&limit={limit}"
            req = urllib.request.Request(fallback_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = []
            for m in data:
                model_id = m.get("id", "")
                models.append({
                    "model_id": model_id,
                    "pipeline_tag": m.get("pipeline_tag", "unknown"),
                    "downloads": m.get("downloads", 0),
                    "likes": m.get("likes", 0),
                    "url": f"https://huggingface.co/{model_id}",
                })
            return models
        except Exception:
            return []


def fetch_hn_ai_pulse(min_points: int = 25, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch top trending AI stories and technical debates from Hacker News via Algolia API."""
    params = {
        "tags": "story",
        "query": "AI OR LLM OR Claude OR OpenAI OR Anthropic OR DeepSeek",
        "numericFilters": f"points>{min_points}",
        "hitsPerPage": str(limit),
    }
    url = f"https://hn.algolia.com/api/v1/search_by_date?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        hits = data.get("hits", [])
        stories = []
        for h in hits:
            title = h.get("title", "")
            points = h.get("points", 0)
            num_comments = h.get("num_comments", 0)
            story_url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            created_at = h.get("created_at", "")

            stories.append({
                "source": "Hacker News AI Pulse",
                "title": title,
                "points": points,
                "comments": num_comments,
                "url": story_url,
                "hn_thread": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "created_at": created_at,
            })
        return stories
    except Exception:
        return []


def fetch_github_trending_ai(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch breakout trending AI & agent repositories from GitHub."""
    params = {
        "q": "topic:llm OR topic:agents OR topic:inference OR topic:vllm",
        "sort": "stars",
        "order": "desc",
        "per_page": str(limit),
    }
    url = f"https://api.github.com/search/repositories?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items = data.get("items", [])
        repos = []
        for r in items:
            repos.append({
                "source": "GitHub Trending AI",
                "repo": r.get("full_name", ""),
                "description": r.get("description", "") or "No description",
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "language": r.get("language", "Unknown"),
                "url": r.get("html_url", ""),
            })
        return repos
    except Exception:
        return []
