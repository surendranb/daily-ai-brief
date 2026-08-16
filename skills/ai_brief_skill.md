---
name: ai_brief_skill
description: Tactical operational playbook for consuming and generating daily AI intelligence briefings, frontier lab radar, and podcast digests.
version: "1.0.0"
---

# Daily AI Brief Playbook

## 1. When to Use
Use this skill when:
- Synthesizing a morning intelligence memo on AI models, tools, preprints, and podcasts.
- Performing competitive reconnaissance on frontier labs (OpenAI, Anthropic, DeepMind, Meta, BAIR, Mistral).
- Tracking open-source model releases, parameter scales, and benchmark claims.
- Summarizing new preprints from arXiv or Hugging Face Daily Papers.
- Extracting insights and guest takeaways from top AI podcasts (Latent Space, Dwarkesh, No Priors, Cognitive Revolution).

## 2. Tool Workflows

### A. The 1-Call Morning Briefing
Call `get_daily_ai_brief()` to produce a structured, high-density intelligence briefing:
```json
{
  "focus_areas": ["frontier_labs", "papers", "podcasts", "community"],
  "date": "latest"
}
```

### B. Tracking Frontier Lab Drops
To monitor official releases, policy updates, and research papers from frontier labs:
```json
{
  "labs": ["deepmind", "bair", "meta", "mistral", "huggingface", "microsoft"],
  "since": "48h"
}
```

### C. Podcast Intelligence
To catch newly released podcast discussions on reasoning models, agent frameworks, or hardware compute:
```json
{
  "podcasts": ["latent_space", "dwarkesh", "no_priors", "cognitive_revolution"],
  "since": "7d"
}
```

## 3. Formatting Standards
- **BLUF First**: Always start with the top 3 headline breakthroughs of the day.
- **Categorized Sections**:
  1. 🚀 **Frontier & Open-Weight Models** (Parameters, License, Benchmarks)
  2. 🔬 **Top Research Preprints** (Problem, Method, Result)
  3. 🎙️ **Podcast Takeaways** (Guest, Core Thesis, Key Timestamps)
  4. ⚡ **Breakout Repos & Ecosystem Debates** (Stars, Consensus)
