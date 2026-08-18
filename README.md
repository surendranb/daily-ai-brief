# ⚡ daily-ai-brief

[![CI](https://github.com/surendranb/daily-ai-brief/actions/workflows/ci.yml/badge.svg)](https://github.com/surendranb/daily-ai-brief/actions)
[![PyPI version](https://img.shields.io/pypi/v/daily-ai-brief.svg?style=flat-square&color=blue)](https://pypi.org/project/daily-ai-brief/)
[![NPM version](https://img.shields.io/npm/v/@surendranb/daily-ai-brief.svg?style=flat-square&color=green)](https://www.npmjs.com/package/@surendranb/daily-ai-brief)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/surendranb/daily-ai-brief/badge)](https://scorecard.dev/viewer/?site=github.com/surendranb/daily-ai-brief)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

> **Dedicated Daily AI Intelligence, Research Preprints, Frontier Models & Podcast Digest Engine for AI Agents and Developers.**

`daily-ai-brief` aggregates, filters, and synthesizes hundreds of sources of daily AI breakthroughs into a single, high-density morning intelligence brief. **Zero API keys, zero tokens wasted, zero configuration required.**

---

## 🚀 Quick Start

### ⚡ Option 1: Universal 1-Line Installer
```bash
curl -fsSL https://daily-ai-brief.builditwithai.xyz/install | bash
```

### 🐍 Option 2: Run via Python (`uvx`)
```bash
uvx daily-ai-brief
```

### 📦 Option 3: Run via Node (`npx`)
```bash
npx -y @surendranb/daily-ai-brief
```

---

## 🛠️ Model Context Protocol (MCP) Setup

Add `daily-ai-brief` directly to your favorite AI agent harness:

### 🤖 Claude Desktop / Claude Code
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "daily-ai-brief": {
      "command": "uvx",
      "args": ["daily-ai-brief"]
    }
  }
}
```

### 💻 Cursor / Windsurf / Antigravity
Add to your IDE MCP settings:
```json
{
  "mcpServers": {
    "daily-ai-brief": {
      "command": "npx",
      "args": ["-y", "@surendranb/daily-ai-brief"]
    }
  }
}
```

---

## 🧭 Intelligence Coverage

`daily-ai-brief` synthesizes 4 real-time layers into a unified daily digest:

1. **🏛️ Frontier AI Labs**: Research announcements and blog posts from Berkeley AI Research (BAIR), Google DeepMind, Meta AI, Mistral AI, Microsoft Research, and Hugging Face.
2. **🔬 Curated Preprints**: Top daily research papers and breakthrough preprints from Hugging Face Daily Papers and arXiv (`cs.AI`, `cs.LG`, `cs.CL`, `stat.ML`).
3. **🎙️ Podcast Insights**: Episode summaries and key takeaways from leading technical discussions (*Latent Space*, *Dwarkesh Podcast*, *No Priors*, *The Cognitive Revolution*, *TWIML AI*).
4. **⚡ Open Weights & Community**: Trending open-source model drops from Hugging Face Hub and trending discussions from Hacker News AI.

---

## 📡 Available Tools

| Tool Name | Parameters | Description |
|---|---|---|
| `get_daily_ai_brief` | `focus_areas`, `date` | 1-call synthesized markdown executive brief across all 4 intelligence layers. |
| `get_frontier_lab_updates` | `labs`, `max_items` | Direct updates from frontier AI research organizations. |
| `get_ai_podcasts` | `podcasts`, `max_items` | Latest technical podcast drops with host and episode summaries. |
| `get_model_drops` | `limit` | Trending open weights, model parameter scales, and download deltas on Hugging Face. |
| `get_arxiv_breakthroughs` | `categories`, `query`, `max_results` | High-impact preprints filtered by topic and community engagement. |
| `skill_read` | `skill_name` | Load bundled operational skills and prompts dynamically. |
| `skills_list` | *(none)* | List available operational skills. |

---

## 🔒 Telemetry

To opt out of anonymous usage telemetry:
```bash
export DO_NOT_TRACK=1
```

---

## 📄 License

MIT License. Free and open source for all developers and AI agents.
