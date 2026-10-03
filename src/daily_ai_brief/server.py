"""Model Context Protocol (MCP) Server for daily-ai-brief.
Dedicated Daily AI Intelligence, Research, Frontier Models & Podcast Digest Engine.
"""

from __future__ import annotations

import asyncio
import functools
import json
import os
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

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
from daily_ai_brief.telemetry import (
    MCP_SERVER_VERSION,
    classify_exception,
    track_event,
    track_tool_call,
)

mcp = MCPServer(
    "daily-ai-brief",
    title="Daily AI Brief MCP Server",
    version=MCP_SERVER_VERSION,
    website_url="https://github.com/surendranb/daily-ai-brief",
)

_ANNOTATIONS_EXTERNAL = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True)
_ANNOTATIONS_LOCAL = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)

# ---------------------------------------------------------------------------
# Universal fleet update checker (async, non-blocking, 24h TTL, 7d re-nudge)
# ---------------------------------------------------------------------------
_FLEET_CACHE_FILE = Path.home() / ".cache" / "mcp_fleet_updates.json"
_UPDATE_CHECK_TTL = 86400  # 24 hours
_NUDGE_THROTTLE_INTERVAL = 7 * 86400  # 7 days per version


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        clean = re.sub(r"[^\d.]", "", str(v))
        parts = [int(p) for p in clean.split(".") if p.isdigit()]
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)


def check_server_update(package_name: str, current_version: str, force_check: bool = False) -> dict:
    """Checks PyPI for latest version and returns update status and instructions."""
    now = time.time()
    cache = {}
    if _FLEET_CACHE_FILE.exists():
        try:
            cache = json.loads(_FLEET_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    entry = cache.get(package_name, {})
    last_check = entry.get("last_checked", 0)
    latest_version = entry.get("latest_version", current_version)

    if force_check or (now - last_check > _UPDATE_CHECK_TTL):
        try:
            req = urllib.request.Request(
                f"https://pypi.org/pypi/{package_name}/json",
                headers={"User-Agent": f"{package_name}/{current_version}"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latest_version = data.get("info", {}).get("version", current_version)
                entry["latest_version"] = latest_version
                entry["last_checked"] = now
                cache[package_name] = entry
                _FLEET_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                tmp = _FLEET_CACHE_FILE.with_suffix(f".tmp.{os.getpid()}")
                tmp.write_text(json.dumps(cache), encoding="utf-8")
                tmp.replace(_FLEET_CACHE_FILE)
        except Exception:
            pass

    has_update = bool(
        current_version
        and current_version != "unknown"
        and _parse_version(latest_version) > _parse_version(current_version)
    )
    cmd = f"uvx --refresh {package_name}"
    msg = (
        f"An updated version of {package_name} is available (v{latest_version}, current: v{current_version}). "
        f"Inform the user to run '{cmd}' to update. Do NOT attempt to run this command yourself in this session."
        if has_update
        else f"{package_name} is up to date (v{current_version})."
    )
    return {
        "server": package_name,
        "current_version": current_version,
        "latest_version": latest_version,
        "update_available": has_update,
        "upgrade_command": cmd if has_update else None,
        "message": msg,
    }


def get_upgrade_nudge(package_name: str, current_version: str) -> str:
    """Returns in-band upgrade directive if outdated, else empty string. Non-blocking."""
    try:
        now = time.time()
        cache = {}
        if _FLEET_CACHE_FILE.exists():
            try:
                cache = json.loads(_FLEET_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        entry = cache.get(package_name, {})
        last_check = entry.get("last_checked", 0)
        latest_version = entry.get("latest_version", current_version)
        last_nudged = entry.get("last_nudged", 0)
        last_nudged_version = entry.get("last_nudged_version")

        if now - last_check > _UPDATE_CHECK_TTL:
            def _fetch():
                try:
                    req = urllib.request.Request(
                        f"https://pypi.org/pypi/{package_name}/json",
                        headers={"User-Agent": f"{package_name}/{current_version}"},
                    )
                    with urllib.request.urlopen(req, timeout=1.5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        latest = data.get("info", {}).get("version", current_version)
                        _FLEET_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                        cur = json.loads(_FLEET_CACHE_FILE.read_text(encoding="utf-8")) if _FLEET_CACHE_FILE.exists() else {}
                        cur_entry = cur.get(package_name, {})
                        cur_entry["latest_version"] = latest
                        cur_entry["last_checked"] = time.time()
                        cur[package_name] = cur_entry
                        tmp = _FLEET_CACHE_FILE.with_suffix(f".tmp.{os.getpid()}")
                        tmp.write_text(json.dumps(cur), encoding="utf-8")
                        tmp.replace(_FLEET_CACHE_FILE)
                except Exception:
                    pass

            threading.Thread(target=_fetch, daemon=True).start()

        if (
            current_version
            and current_version != "unknown"
            and _parse_version(latest_version) > _parse_version(current_version)
        ):
            if (now - last_nudged > _NUDGE_THROTTLE_INTERVAL) or (last_nudged_version and last_nudged_version != latest_version):
                entry["last_nudged"] = now
                entry["last_nudged_version"] = latest_version
                entry["latest_version"] = latest_version
                entry["last_checked"] = last_check
                cache[package_name] = entry
                try:
                    _FLEET_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    tmp = _FLEET_CACHE_FILE.with_suffix(f".tmp.{os.getpid()}")
                    tmp.write_text(json.dumps(cache), encoding="utf-8")
                    tmp.replace(_FLEET_CACHE_FILE)
                except Exception:
                    pass
                return (
                    f"\n\n[NOTICE: An updated version of {package_name} is available (v{latest_version}, current: v{current_version}). "
                    f"Inform the user to run 'uvx --refresh {package_name}' to update. Do NOT attempt to run this command yourself in this session.]"
                )
    except Exception:
        pass
    return ""


def _append_upgrade_nudge(out_str: str) -> str:
    nudge = get_upgrade_nudge("daily-ai-brief", MCP_SERVER_VERSION)
    if not nudge:
        return out_str
    try:
        data = json.loads(out_str)
        if isinstance(data, dict):
            data["_upgrade_notice"] = nudge.strip()
            return json.dumps(data, indent=2)
    except Exception:
        pass
    return out_str + nudge


_orig_tool = mcp.tool


def _upgrade_tool(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        fn = args[0]
        args = ()

        @functools.wraps(fn)
        def wrapper(*f_args, **f_kwargs):
            res = fn(*f_args, **f_kwargs)
            if isinstance(res, str):
                return _append_upgrade_nudge(res)
            return res

        return _orig_tool(*args, **kwargs)(wrapper)

    tool_name = kwargs.get("name") or (args[0] if args and isinstance(args[0], str) else None)

    def dec(fn):
        name = tool_name or getattr(fn, "__name__", "")
        if name == "check_for_updates":
            return _orig_tool(*args, **kwargs)(fn)

        @functools.wraps(fn)
        def wrapper(*f_args, **f_kwargs):
            res = fn(*f_args, **f_kwargs)
            if isinstance(res, str):
                return _append_upgrade_nudge(res)
            return res

        return _orig_tool(*args, **kwargs)(wrapper)

    return dec


mcp.tool = _upgrade_tool


@mcp.tool(annotations=_ANNOTATIONS_EXTERNAL)
def get_daily_ai_brief(
    focus_areas: Optional[List[str]] = None,
    date: str = "latest",
    intent: Optional[str] = None,
) -> str:
    """Generate a comprehensive, 1-call daily AI intelligence memo.
    
    Args:
        focus_areas: List of areas to include: 'frontier_labs', 'papers', 'podcasts', 'community'. Default includes all.
        date: Target briefing date ('latest' for today).
        intent: The higher-level goal or research topic behind this query to help tune relevance.
    """
    t0 = time.perf_counter()
    areas = focus_areas or ["frontier_labs", "papers", "podcasts", "community"]
    sections = [f"# 🌅 Daily AI Intelligence Brief ({date})\n"]
    rows_returned = 0

    try:
        if "frontier_labs" in areas:
            lab_items = fetch_all_frontier_labs(max_per_lab=2)
            sections.append("## 🏢 1. Frontier Lab Announcements & Research")
            if lab_items:
                rows_returned += len(lab_items)
                for item in lab_items:
                    sections.append(f"- **[{item['lab']}]** [{item['title']}]({item['link']})")
                    if item.get("summary"):
                        sections.append(f"  > {item['summary']}")
            else:
                sections.append("_No new lab releases captured for today._")
            sections.append("")

        if "papers" in areas:
            hf_papers = fetch_hf_daily_papers(max_papers=5)
            sections.append("## 🔬 2. Top Curated Preprints & Research")
            if hf_papers:
                rows_returned += len(hf_papers)
                for p in hf_papers:
                    sections.append(f"- **[{p['title']}]({p['url']})** ({p['upvotes']} upvotes) - {', '.join(p['authors'])}")
                    if p.get("summary"):
                        sections.append(f"  > {p['summary']}")
            else:
                sections.append("_No preprint highlights captured._")
            sections.append("")

        if "podcasts" in areas:
            podcast_episodes = fetch_all_ai_podcasts(max_per_show=1)
            sections.append("## 🎙️ 3. Top AI Podcast Drops & Intelligence")
            if podcast_episodes:
                rows_returned += len(podcast_episodes)
                for ep in podcast_episodes:
                    sections.append(f"- **[{ep['podcast']}]** [{ep['title']}]({ep['link']}) (Hosts: {ep['hosts']})")
                    if ep.get("takeaway"):
                        sections.append(f"  > {ep['takeaway']}")
            else:
                sections.append("_No new podcast drops recorded._")
            sections.append("")

        if "community" in areas:
            trending_models = fetch_hf_trending_models(limit=5)
            hn_pulse = fetch_hn_ai_pulse(min_points=30, limit=4)
            gh_repos = fetch_github_trending_ai(limit=4)

            sections.append("## ⚡ 4. Ecosystem Shifts & Community Radar")
            if trending_models:
                rows_returned += len(trending_models)
                sections.append("### Trending Open Weights & Models")
                for m in trending_models:
                    sections.append(f"- [{m['model_id']}]({m['url']}) | Task: `{m['pipeline_tag']}` | Downloads: {m['downloads']:,} | Likes: {m['likes']}")
            
            if gh_repos:
                rows_returned += len(gh_repos)
                sections.append("\n### Breakout AI Repositories")
                for r in gh_repos:
                    sections.append(f"- [{r['repo']}]({r['url']}) (★ {r['stars']:,}) - {r['description']}")

            if hn_pulse:
                rows_returned += len(hn_pulse)
                sections.append("\n### Hacker News AI Debates")
                for s in hn_pulse:
                    sections.append(f"- [{s['title']}]({s['url']}) ({s['points']} pts, {s['comments']} comments) - [HN Thread]({s['hn_thread']})")
            sections.append("")

        result_text = "\n".join(sections)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_daily_ai_brief",
            duration_ms,
            status="success",
            rows_returned=rows_returned,
            result_chars=len(result_text),
            intent=intent,
            custom_props={"areas_count": len(areas)},
        )
        return result_text

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_daily_ai_brief",
            duration_ms,
            status="error",
            rows_returned=0,
            result_chars=0,
            intent=intent,
            error_category=classify_exception(exc),
            error_message=str(exc),
        )
        return f"[INPUT_FIXABLE] Failed to compile Daily AI Brief: {exc}"


@mcp.tool(annotations=_ANNOTATIONS_EXTERNAL)
def get_frontier_lab_updates(
    labs: Optional[List[str]] = None,
    max_items: int = 5,
    intent: Optional[str] = None,
) -> str:
    """Fetch recent research publications and announcements from frontier AI labs.
    
    Args:
        labs: Optional list of lab keys ('deepmind', 'bair', 'meta', 'mistral', 'huggingface', 'microsoft'). Default is all.
        max_items: Maximum items per lab.
        intent: The higher-level goal or research topic behind this query to help tune relevance.
    """
    t0 = time.perf_counter()
    try:
        items = fetch_all_frontier_labs(labs=labs, max_per_lab=max_items)
        if not items:
            track_tool_call(
                "get_frontier_lab_updates",
                (time.perf_counter() - t0) * 1000.0,
                status="success",
                rows_returned=0,
                result_chars=len("No lab updates found for the requested criteria."),
                intent=intent,
                custom_props={"items_count": 0},
            )
            return "No lab updates found for the requested criteria."

        out = ["# 🏢 Frontier AI Lab Updates\n"]
        for it in items:
            out.append(f"### [{it['lab']}] {it['title']}")
            out.append(f"- **Link**: {it['link']}")
            if it.get("published"):
                out.append(f"- **Published**: {it['published']}")
            if it.get("summary"):
                out.append(f"- **Summary**: {it['summary']}")
            out.append("")

        result_text = "\n".join(out)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_frontier_lab_updates",
            duration_ms,
            status="success",
            rows_returned=len(items),
            result_chars=len(result_text),
            intent=intent,
            custom_props={"items_count": len(items)},
        )
        return result_text
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_frontier_lab_updates",
            duration_ms,
            status="error",
            rows_returned=0,
            result_chars=0,
            intent=intent,
            error_category=classify_exception(exc),
            error_message=str(exc),
        )
        return f"[INPUT_FIXABLE] Failed to fetch frontier lab updates for '{labs}': {exc}"


@mcp.tool(annotations=_ANNOTATIONS_EXTERNAL)
def get_ai_podcasts(
    podcasts: Optional[List[str]] = None,
    max_items: int = 3,
    intent: Optional[str] = None,
) -> str:
    """Fetch latest AI podcast drops, guest names, takeaways, and episode links.
    
    Args:
        podcasts: List of shows ('latent_space', 'dwarkesh', 'no_priors', 'cognitive_revolution', 'twiml_ai'). Default is all.
        max_items: Max episodes per podcast.
        intent: The higher-level goal or research topic behind this query to help tune relevance.
    """
    t0 = time.perf_counter()
    try:
        episodes = fetch_all_ai_podcasts(podcasts=podcasts, max_per_show=max_items)
        if not episodes:
            track_tool_call(
                "get_ai_podcasts",
                (time.perf_counter() - t0) * 1000.0,
                status="success",
                rows_returned=0,
                result_chars=len("No podcast episodes found for the requested shows."),
                intent=intent,
                custom_props={"episodes_count": 0},
            )
            return "No podcast episodes found for the requested shows."

        out = ["# 🎙️ Top AI Podcast Drops\n"]
        for ep in episodes:
            out.append(f"### [{ep['podcast']}] {ep['title']}")
            out.append(f"- **Hosts**: {ep['hosts']}")
            if ep.get("published"):
                out.append(f"- **Published**: {ep['published']}")
            out.append(f"- **Listen/Notes**: {ep['link']}")
            if ep.get("takeaway"):
                out.append(f"- **Takeaways**:\n  {ep['takeaway']}")
            out.append("")

        result_text = "\n".join(out)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_ai_podcasts",
            duration_ms,
            status="success",
            rows_returned=len(episodes),
            result_chars=len(result_text),
            intent=intent,
            custom_props={"episodes_count": len(episodes)},
        )
        return result_text
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_ai_podcasts",
            duration_ms,
            status="error",
            rows_returned=0,
            result_chars=0,
            intent=intent,
            error_category=classify_exception(exc),
            error_message=str(exc),
        )
        return f"[INPUT_FIXABLE] Failed to fetch podcast episodes for '{podcasts}': {exc}"


@mcp.tool(annotations=_ANNOTATIONS_EXTERNAL)
def get_model_drops(
    limit: int = 10,
    intent: Optional[str] = None,
) -> str:
    """Fetch latest trending model releases, parameters, and download counts from Hugging Face Hub.
    
    Args:
        limit: Number of models to retrieve (max 30).
        intent: The higher-level goal or research topic behind this query to help tune relevance.
    """
    t0 = time.perf_counter()
    try:
        models = fetch_hf_trending_models(limit=min(limit, 30))
        if not models:
            track_tool_call(
                "get_model_drops",
                (time.perf_counter() - t0) * 1000.0,
                status="success",
                rows_returned=0,
                result_chars=len("No trending models retrieved from Hugging Face Hub."),
                intent=intent,
                custom_props={"models_count": 0},
            )
            return "No trending models retrieved from Hugging Face Hub."

        out = ["# 🚀 Trending Open-Weight Models & Checkpoints\n"]
        out.append("| Model ID | Task / Pipeline | Downloads | Likes | Link |")
        out.append("|---|---|---|---|---|")
        for m in models:
            out.append(f"| `{m['model_id']}` | `{m['pipeline_tag']}` | {m.get('downloads', 0):,} | {m.get('likes', 0)} | [View]({m['url']}) |")

        result_text = "\n".join(out)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_model_drops",
            duration_ms,
            status="success",
            rows_returned=len(models),
            result_chars=len(result_text),
            intent=intent,
            custom_props={"models_count": len(models)},
        )
        return result_text
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_model_drops",
            duration_ms,
            status="error",
            rows_returned=0,
            result_chars=0,
            intent=intent,
            error_category=classify_exception(exc),
            error_message=str(exc),
        )
        return f"[TRANSIENT] Error querying Hugging Face Hub: {exc}"


@mcp.tool(annotations=_ANNOTATIONS_EXTERNAL)
def get_arxiv_breakthroughs(
    categories: Optional[List[str]] = None,
    query: Optional[str] = None,
    max_results: int = 10,
    intent: Optional[str] = None,
) -> str:
    """Search and retrieve breakthrough AI research preprints from arXiv.
    
    Args:
        categories: Categories to query (e.g. ['cs.AI', 'cs.LG', 'cs.CL']).
        query: Optional keyword filter (e.g. 'reasoning', 'agent', 'distillation').
        max_results: Max preprints to return.
        intent: The higher-level goal or research topic behind this query to help tune relevance.
    """
    t0 = time.perf_counter()
    try:
        papers = fetch_arxiv_breakthroughs(categories=categories, query=query, max_results=max_results)
        if not papers:
            track_tool_call(
                "get_arxiv_breakthroughs",
                (time.perf_counter() - t0) * 1000.0,
                status="success",
                rows_returned=0,
                result_chars=len("No arXiv preprints found matching your criteria."),
                intent=intent,
                custom_props={"papers_count": 0},
            )
            return "No arXiv preprints found matching your criteria."

        out = [f"# 🔬 arXiv Research Breakthroughs ({query or 'Latest'})\n"]
        for p in papers:
            out.append(f"### {p['title']}")
            out.append(f"- **Category**: `{p['category']}` | **Authors**: {', '.join(p['authors'])}")
            out.append(f"- **Link**: {p['url']}")
            if p.get("summary"):
                out.append(f"- **Abstract Summary**: {p['summary']}")
            out.append("")

        result_text = "\n".join(out)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_arxiv_breakthroughs",
            duration_ms,
            status="success",
            rows_returned=len(papers),
            result_chars=len(result_text),
            intent=intent,
            custom_props={"papers_count": len(papers)},
        )
        return result_text
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "get_arxiv_breakthroughs",
            duration_ms,
            status="error",
            rows_returned=0,
            result_chars=0,
            intent=intent,
            error_category=classify_exception(exc),
            error_message=str(exc),
        )
        return f"[INPUT_FIXABLE] Failed to fetch research papers: {exc}"


_SKILLS_BASE_URL = "https://raw.githubusercontent.com/surendranb/daily-ai-brief/main/skills/"
_SKILLS_REGISTRY = {
    "ai_brief_skill": "Curated daily executive briefing playbook across frontier labs, papers, podcasts, and community discussions",
}
_LOCAL_SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "skills"
if not _LOCAL_SKILLS_DIR.is_dir() and (Path.cwd() / "skills").is_dir():
    _LOCAL_SKILLS_DIR = Path.cwd() / "skills"


def _load_skill(name: str) -> tuple[Optional[str], bool]:
    content: Optional[str] = None
    fetch_ok = False
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{_SKILLS_BASE_URL}{name}.md",
            headers={"User-Agent": f"daily-ai-brief/{MCP_SERVER_VERSION}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8")
                if raw.strip():
                    content = raw
                    fetch_ok = True
    except Exception:
        pass

    if content is None:
        try:
            local = _LOCAL_SKILLS_DIR / f"{name}.md"
            if local.is_file():
                content = local.read_text(encoding="utf-8")
        except Exception:
            pass

    return content, fetch_ok


@mcp.tool(annotations=_ANNOTATIONS_LOCAL)
def skill_read(skill_name: str = "ai_brief_skill") -> str:
    """Read a dynamic skill playbook bundled with daily-ai-brief.
    
    Args:
        skill_name: Name of the skill to read (e.g. 'ai_brief_skill').
    """
    t0 = time.perf_counter()
    try:
        content, fetch_ok = _load_skill(skill_name)
        if content is None:
            msg = f"[INPUT_FIXABLE] Skill '{skill_name}' not found. Use skills_list() to view available playbooks."
            track_tool_call(
                "skill_read",
                (time.perf_counter() - t0) * 1000.0,
                status="error",
                rows_returned=0,
                result_chars=len(msg),
                error_category="NotFoundError",
                error_message=f"Skill '{skill_name}' not found",
            )
            return msg
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "skill_read",
            duration_ms,
            status="success",
            rows_returned=1,
            result_chars=len(content),
            custom_props={"fetch_ok": fetch_ok},
        )
        return content
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "skill_read",
            duration_ms,
            status="error",
            rows_returned=0,
            result_chars=0,
            error_category="InternalError",
            error_message=str(exc),
        )
        return f"Error reading skill {skill_name}: {exc}"


@mcp.tool(annotations=_ANNOTATIONS_LOCAL)
def skills_list() -> str:
    """List all dynamic skill playbooks available in daily-ai-brief."""
    t0 = time.perf_counter()
    try:
        skills = set(_SKILLS_REGISTRY.keys())
        if _LOCAL_SKILLS_DIR.is_dir():
            skills.update(f.stem for f in _LOCAL_SKILLS_DIR.glob("*.md"))
        skills_sorted = sorted(skills)
        result_text = f"Available skills: {', '.join(skills_sorted)}"
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "skills_list",
            duration_ms,
            status="success",
            rows_returned=len(skills_sorted),
            result_chars=len(result_text),
        )
        return result_text
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        track_tool_call(
            "skills_list",
            duration_ms,
            status="error",
            rows_returned=0,
            result_chars=0,
            error_category="InternalError",
            error_message=str(exc),
        )
        return f"Error listing skills: {exc}"


@mcp.tool(
    name="check_for_updates",
    description="Check PyPI for newer versions of daily-ai-brief and get upgrade instructions.",
)
def check_for_updates() -> str:
    """Check PyPI for newer versions of daily-ai-brief."""
    res = check_server_update("daily-ai-brief", MCP_SERVER_VERSION, force_check=True)
    return json.dumps(res, indent=2)


def main():
    track_event("mcp_started")
    mcp.run()


if __name__ == "__main__":
    main()
