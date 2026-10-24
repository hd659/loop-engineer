"""
Builder Persona (`hd`) and Project Selection Filter.

Grounds all synthesized project ideas and daily commits in Haodong Huang's real
engineering profile, cognitive models, and aesthetic standards:
- Anti-bluff, high-leverage Indie Builder (`hd`)
- Eliminates repetitive manual friction via automation & MCP bridges
- Builds production-grade AI infrastructure, multi-agent harnesses, and quota routers
- Explores quantitative finance, compliant digital assets (EVM/RWA), and robust ML/FL
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ProjectPillar:
    slug: str
    title: str
    description: str
    keywords: List[str]
    tech_stack: List[str]


@dataclass(frozen=True)
class BuilderPersona:
    handle: str = "hd"
    role: str = "CS & Data Science Builder · AI Infra, Automation & Quant Engineering"
    style_guidelines: List[str] = field(
        default_factory=lambda: [
            "Minimalist, direct, zero-hype documentation (cold, precise engineering tone).",
            "First-principles architecture: solve real friction or structural bottlenecks, never toy CRUD.",
            "Every commit must include runnable code or deterministic tests (pytest / foundry).",
            "Strict privacy hygiene: zero personal credentials, student IDs, or private server IPs.",
        ]
    )
    anti_patterns: List[str] = field(
        default_factory=lambda: [
            "todo-list",
            "weather-app",
            "calculator-demo",
            "generic-blog-template",
            "empty-boilerplate",
        ]
    )
    pillars: Dict[str, ProjectPillar] = field(
        default_factory=lambda: {
            "workflow-mcp": ProjectPillar(
                slug="workflow-mcp",
                title="Workflow Automation & MCP Bridges",
                description="Eliminating repetitive manual actions across university LMS, email, network diagnostics, and media pipelines.",
                keywords=[
                    "mcp", "moodle", "edstem", "attendance", "mail", "playwright",
                    "automation", "avassetwriter", "video", "network", "dns", "ipv6", "tailscale",
                ],
                tech_stack=["Python", "FastMCP", "AsyncIO", "Playwright", "Swift"],
            ),
            "ai-infra-harness": ProjectPillar(
                slug="ai-infra-harness",
                title="AI Gateway Infra & Multi-Agent Harness",
                description="Perishable LLM quota arbitrage, rolling-window scheduling, prompt-cache affinity, and cross-client agent harness sync.",
                keywords=[
                    "gateway", "quota", "cache", "claude", "gemini", "codex", "pi",
                    "antigravity", "cursor", "harness", "purge", "brokenpipe", "protobuf", "token",
                ],
                tech_stack=["Python", "TypeScript", "SQLite", "HTTP/SSE", "JSON-Schema"],
            ),
            "quant-fintech-web3": ProjectPillar(
                slug="quant-fintech-web3",
                title="Quant Finance, Compliant Web3 & Robust ML",
                description="EVM delta-neutral vaults, perpetuals funding-rate microstructure, grid execution, and Byzantine-resilient federated learning.",
                keywords=[
                    "quant", "grid", "okx", "btc", "funding", "perps", "evm", "solidity",
                    "blockchain", "rwa", "vault", "federated", "poisoning", "byzantine",
                ],
                tech_stack=["Python", "Solidity", "NumPy", "PyTest", "AsyncIO"],
            ),
            "cognitive-systems": ProjectPillar(
                slug="cognitive-systems",
                title="Transaction-Cost & Decision Systems",
                description="Executable simulations of transaction-cost economics, perishable capacity models, and linguistic stylometry.",
                keywords=[
                    "transaction-cost", "perishable", "arbitrage", "bayes", "deconstruction",
                    "stylometry", "gptzero", "rewrite", "entropy",
                ],
                tech_stack=["Python", "TypeScript", "CLI"],
            ),
        }
    )

    def classify_topic(self, text: str) -> str:
        """Classify arbitrary conversation or diary text into the best-matching engineering pillar."""
        lowered = (text or "").lower()
        scores: Dict[str, int] = {slug: 0 for slug in self.pillars}
        for slug, pillar in self.pillars.items():
            for kw in pillar.keywords:
                if kw.lower() in lowered:
                    scores[slug] += 2
        best_slug = max(scores.items(), key=lambda item: item[1])[0]
        if scores[best_slug] == 0:
            return "ai-infra-harness"
        return best_slug


DEFAULT_PERSONA = BuilderPersona()
