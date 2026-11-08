# Setting Up Daily AI Brief MCP Server

A zero-configuration MCP server for automated daily AI intelligence, research breakthroughs, frontier model releases, and podcast digests.

Official Repository: [github.com/surendranb/daily-ai-brief](https://github.com/surendranb/daily-ai-brief)

---

## 1. Quickstart (Zero API Keys Required)

`daily-ai-brief` aggregates public RSS feeds, arXiv preprints, frontier lab research blogs, and Hugging Face model drops. **No API keys or credentials are required to start.**

---

## 2. Client Configuration

### Claude Desktop (`claude_desktop_config.json`)
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

### Cursor (`.cursor/mcp.json`)
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

### Command Line / CLI Testing
```bash
uvx daily-ai-brief
```

---

## 3. Core Tools & Workflow

1. **`get_daily_ai_brief()`**:
   Generates a structured daily briefing combining:
   - Frontier lab updates (OpenAI, Anthropic, Google DeepMind, Meta AI)
   - Highest-signal arXiv breakthroughs in `cs.AI`, `cs.CL`, `cs.CV`, `cs.LG`
   - Latest podcast episodes (Dwarkesh Patel, Latent Space, No Priors, TWIML)
   - New model weights & releases

2. **`get_frontier_lab_updates(labs=[...])`**:
   Filter specific research labs (e.g. `["openai", "anthropic", "deepmind"]`).

3. **`get_arxiv_breakthroughs(categories=[...])`**:
   Retrieve top recent research papers filtered by subject categories.

4. **`get_ai_podcasts(podcasts=[...])`**:
   Inspect recent conversations with AI leaders and researchers.

5. **`get_model_drops(limit=10)`**:
   Inspect newly released open-weights and proprietary model releases.

---

## 4. Troubleshooting & Offline Behavior

* **Network Latency / Feed Outages**: Fetchers gracefully degrade. If one source fails, the remaining channels still compile into the brief.
* **Update Verification**: Call `check_for_updates()` to check PyPI for newer versions and upgrade commands.
* **Dynamic Skills**: Call `skill_read(skill_name='ai_brief_skill')` for instructions on synthesizing executive briefings.
