"""AI Podcasts & Audio Intelligence Fetcher.
Zero-auth podcast RSS ingestion for top AI shows: Latent Space, Dwarkesh, No Priors, Cognitive Revolution, TWIML AI, Practical AI.
"""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


PODCAST_FEEDS = {
    "latent_space": {
        "name": "Latent Space (The AI Engineer Podcast)",
        "hosts": "Swyx & Alessio",
        "url": "https://api.substack.com/feed/podcast/1084089.rss",
    },
    "dwarkesh": {
        "name": "The Dwarkesh Podcast",
        "hosts": "Dwarkesh Patel",
        "url": "https://api.substack.com/feed/podcast/6216.rss",
    },
    "no_priors": {
        "name": "No Priors: Early Stage AI, Investors and Founders",
        "hosts": "Elad Gil & Sarah Guo",
        "url": "https://feeds.megaphone.fm/NOPRIORS",
    },
    "cognitive_revolution": {
        "name": "The Cognitive Revolution: AI Builders & Researchers",
        "hosts": "Nathan Labenz",
        "url": "https://feeds.megaphone.fm/TCR9310860533",
    },
    "twiml_ai": {
        "name": "TWIML AI Podcast",
        "hosts": "Sam Charrington",
        "url": "https://twimlai.com/feed/podcast",
    },
}

USER_AGENT = "daily-ai-brief/0.1.0 (https://github.com/surendranb/daily-ai-brief; ai-podcast-bot)"


def _clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    cleanr = re.compile("<.*?>")
    text = re.sub(cleanr, "", raw_html)
    return " ".join(text.split()).strip()


def fetch_podcast_episodes(podcast_key: str, max_episodes: int = 3) -> List[Dict[str, Any]]:
    config = PODCAST_FEEDS.get(podcast_key.lower())
    if not config:
        return []

    try:
        req = urllib.request.Request(
            config["url"],
            headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/xml, */*"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()

        root = ET.fromstring(data)
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else root.findall(".//item")

        episodes = []
        for item in items[:max_episodes]:
            title = item.findtext("title", default="")
            link = item.findtext("link", default="")
            pub_date = item.findtext("pubDate", default="")
            description = item.findtext("description", default="")

            # Extract enclosure audio url if present
            enclosure = item.find("enclosure")
            audio_url = enclosure.get("url") if enclosure is not None else ""

            clean_desc = _clean_html(description)

            episodes.append({
                "podcast": config["name"],
                "hosts": config["hosts"],
                "title": title.strip(),
                "published": pub_date.strip(),
                "link": link.strip() or audio_url,
                "takeaway": clean_desc[:400] + ("..." if len(clean_desc) > 400 else ""),
            })
        return episodes
    except Exception:
        return []


def fetch_all_ai_podcasts(podcasts: Optional[List[str]] = None, max_per_show: int = 2) -> List[Dict[str, Any]]:
    targets = podcasts if podcasts else list(PODCAST_FEEDS.keys())
    results: List[Dict[str, Any]] = []
    for key in targets:
        show_items = fetch_podcast_episodes(key, max_episodes=max_per_show)
        results.extend(show_items)
    return results
