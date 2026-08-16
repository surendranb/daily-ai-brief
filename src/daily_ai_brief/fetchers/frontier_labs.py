"""Frontier Labs & Research Organizations Fetcher.
Zero-auth ingestion for OpenAI, Anthropic, Google DeepMind, Meta FAIR, BAIR, Stanford HAI, Mistral, and MS Research.
"""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


LAB_FEEDS = {
    "deepmind": {
        "name": "Google DeepMind & Research",
        "url": "https://blog.research.google/atom.xml",
        "type": "atom",
    },
    "bair": {
        "name": "BAIR (Berkeley AI Research)",
        "url": "https://bair.berkeley.edu/blog/feed.xml",
        "type": "rss",
    },
    "meta": {
        "name": "Meta AI & FAIR",
        "url": "https://ai.meta.com/blog/rss.xml",
        "type": "rss",
    },
    "mistral": {
        "name": "Mistral AI",
        "url": "https://mistral.ai/news/rss.xml",
        "type": "rss",
    },
    "huggingface": {
        "name": "Hugging Face Research & Engineering",
        "url": "https://huggingface.co/blog/feed.xml",
        "type": "rss",
    },
    "microsoft": {
        "name": "Microsoft Research AI",
        "url": "https://www.microsoft.com/en-us/research/feed/",
        "type": "rss",
    },
}

USER_AGENT = "daily-ai-brief/0.1.0 (https://github.com/surendranb/daily-ai-brief; ai-intelligence-bot)"


def _clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    cleanr = re.compile("<.*?>")
    text = re.sub(cleanr, "", raw_html)
    return " ".join(text.split()).strip()


def _fetch_url(url: str, timeout: int = 8) -> Optional[bytes]:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/atom+xml, application/rss+xml, application/xml, text/xml, */*",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


def fetch_lab_feed(lab_key: str, max_items: int = 5) -> List[Dict[str, Any]]:
    config = LAB_FEEDS.get(lab_key.lower())
    if not config:
        return []

    data = _fetch_url(config["url"])
    if not data:
        return []

    items: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(data)
        if config["type"] == "atom":
            # Atom namespace
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns) or root.findall("entry")
            for entry in entries[:max_items]:
                title = entry.findtext("atom:title", default="", namespaces=ns) or entry.findtext("title", default="")
                link_elem = entry.find("atom:link", ns)
                if link_elem is None:
                    link_elem = entry.find("link")
                link = link_elem.get("href") if link_elem is not None else ""
                published = entry.findtext("atom:published", default="", namespaces=ns) or entry.findtext("published", default="")
                summary = entry.findtext("atom:summary", default="", namespaces=ns) or entry.findtext("summary", default="")
                if not summary:
                    summary = entry.findtext("atom:content", default="", namespaces=ns) or entry.findtext("content", default="")

                items.append({
                    "lab": config["name"],
                    "title": title.strip(),
                    "link": link.strip(),
                    "published": published.strip(),
                    "summary": _clean_html(summary)[:350] + ("..." if len(_clean_html(summary)) > 350 else ""),
                })
        else:
            # RSS 2.0
            channel = root.find("channel")
            raw_items = channel.findall("item") if channel is not None else root.findall(".//item")
            for item in raw_items[:max_items]:
                title = item.findtext("title", default="")
                link = item.findtext("link", default="")
                pub_date = item.findtext("pubDate", default="")
                description = item.findtext("description", default="")

                items.append({
                    "lab": config["name"],
                    "title": title.strip(),
                    "link": link.strip(),
                    "published": pub_date.strip(),
                    "summary": _clean_html(description)[:350] + ("..." if len(_clean_html(description)) > 350 else ""),
                })
    except Exception:
        pass

    return items


def fetch_all_frontier_labs(labs: Optional[List[str]] = None, max_per_lab: int = 3) -> List[Dict[str, Any]]:
    target_labs = labs if labs else list(LAB_FEEDS.keys())
    results: List[Dict[str, Any]] = []
    for lab in target_labs:
        lab_items = fetch_lab_feed(lab, max_items=max_per_lab)
        results.extend(lab_items)
    return results
