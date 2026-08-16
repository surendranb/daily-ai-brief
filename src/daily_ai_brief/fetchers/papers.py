"""Research Papers Fetcher.
Zero-auth ingestion for Hugging Face Daily Papers API and arXiv Preprints (cs.AI, cs.LG, cs.CL, stat.ML).
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


USER_AGENT = "daily-ai-brief/0.1.0 (https://github.com/surendranb/daily-ai-brief; ai-paper-bot)"


def _clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = " ".join(raw.split()).strip()
    return text


def fetch_hf_daily_papers(max_papers: int = 10) -> List[Dict[str, Any]]:
    """Fetch top curated daily AI papers from Hugging Face Daily Papers API."""
    url = "https://huggingface.co/api/daily_papers"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        papers = []
        for item in data[:max_papers]:
            paper = item.get("paper", {})
            paper_id = paper.get("id", "")
            title = _clean_text(paper.get("title", ""))
            summary = _clean_text(paper.get("summary", ""))
            upvotes = paper.get("upvotes", 0)
            authors = [a.get("name", "") for a in paper.get("authors", []) if a.get("name")]
            published_at = item.get("publishedAt", "") or paper.get("publishedAt", "")

            papers.append({
                "source": "Hugging Face Daily Papers",
                "arxiv_id": paper_id,
                "title": title,
                "authors": authors[:5],
                "upvotes": upvotes,
                "published_at": published_at,
                "summary": summary[:400] + ("..." if len(summary) > 400 else ""),
                "url": f"https://huggingface.co/papers/{paper_id}" if paper_id else "",
            })
        return papers
    except Exception:
        return []


def fetch_arxiv_breakthroughs(
    categories: Optional[List[str]] = None,
    query: Optional[str] = None,
    max_results: int = 10,
    sort_by: str = "submittedDate",
) -> List[Dict[str, Any]]:
    """Fetch preprints directly from the official arXiv export API."""
    cats = categories or ["cs.AI", "cs.LG", "cs.CL"]
    cat_query = " OR ".join([f"cat:{c}" for c in cats])

    if query:
        search_query = f"({cat_query}) AND all:{query}"
    else:
        search_query = cat_query

    params = {
        "search_query": search_query,
        "start": "0",
        "max_results": str(max_results),
        "sortBy": sort_by,
        "sortOrder": "descending",
    }
    url = f"http://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=12) as resp:
            xml_data = resp.read()

        root = ET.fromstring(xml_data)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        results = []
        for entry in root.findall("atom:entry", ns):
            title = _clean_text(entry.findtext("atom:title", default="", namespaces=ns))
            summary = _clean_text(entry.findtext("atom:summary", default="", namespaces=ns))
            published = entry.findtext("atom:published", default="", namespaces=ns)
            paper_url = entry.findtext("atom:id", default="", namespaces=ns)

            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.findtext("atom:name", default="", namespaces=ns)
                if name:
                    authors.append(name)

            primary_cat = entry.find("arxiv:primary_category", ns)
            cat_label = primary_cat.get("term") if primary_cat is not None else "cs.AI"

            results.append({
                "source": "arXiv",
                "category": cat_label,
                "title": title,
                "authors": authors[:5],
                "published": published,
                "summary": summary[:400] + ("..." if len(summary) > 400 else ""),
                "url": paper_url,
            })
        return results
    except Exception:
        return []
