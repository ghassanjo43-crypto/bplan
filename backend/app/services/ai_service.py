"""AI narrative generation service.

Responsibilities:
  * a small provider abstraction over OpenAI / Anthropic (chosen via env),
  * best-effort enrichment of the prompt with read-only project data,
  * a single ``generate`` entrypoint used by the route.

Safety: this module NEVER writes to the project and NEVER touches the financial
calculation engine. It only *reads* already-computed figures (via the statement
services) to give the model context, wrapped in try/except so a project missing
data can still generate narrative. API keys are read only from the backend
environment (``app.config.settings``) and are never returned to the caller.
"""
from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..config import settings
from ..models import BusinessPlanProject
from ..schemas.ai import AiGenerateRequest, AiGenerateResponse

logger = logging.getLogger("businessplan.ai")


class AiNotConfiguredError(Exception):
    """No usable AI provider/key is configured (→ 503)."""


class AiProviderError(Exception):
    """The configured provider was reached but failed (→ 502)."""


@dataclass(frozen=True)
class ProviderConfig:
    provider: str          # "openai" | "anthropic"
    model: str
    api_key: str


# --------------------------------------------------------------------------
# provider resolution
# --------------------------------------------------------------------------
_NOT_CONFIGURED_MSG = (
    "AI generation is not configured on the server. Set AI_PROVIDER and the "
    "matching API key (OPENAI_API_KEY or ANTHROPIC_API_KEY) in the backend "
    "environment to enable it."
)


def resolve_provider() -> ProviderConfig:
    """Pick the provider+model+key from settings, or raise AiNotConfiguredError.

    An explicit ``AI_PROVIDER`` wins; otherwise infer from whichever key is set.
    """
    provider = (settings.ai_provider or "").lower()
    if not provider:
        if settings.openai_api_key:
            provider = "openai"
        elif settings.anthropic_api_key:
            provider = "anthropic"
        else:
            raise AiNotConfiguredError(_NOT_CONFIGURED_MSG)

    if provider == "openai":
        if not settings.openai_api_key:
            raise AiNotConfiguredError(_NOT_CONFIGURED_MSG)
        return ProviderConfig("openai", settings.openai_model, settings.openai_api_key)
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise AiNotConfiguredError(_NOT_CONFIGURED_MSG)
        return ProviderConfig("anthropic", settings.anthropic_model, settings.anthropic_api_key)
    raise AiNotConfiguredError(
        f"Unknown AI_PROVIDER '{provider}'. Use 'openai' or 'anthropic'."
    )


# --------------------------------------------------------------------------
# context enrichment (read-only)
# --------------------------------------------------------------------------
def _default_scenario(project: BusinessPlanProject):
    for s in project.scenarios:
        if getattr(s, "is_default", False):
            return s
    return project.scenarios[0] if project.scenarios else None


def build_context(project: BusinessPlanProject) -> str:
    """Assemble a compact, human-readable project brief for the model.

    Every block is guarded: a project missing setup / products / statements still
    yields whatever context is available rather than failing.
    """
    from . import report_data_service as rd

    setup = project.setup
    lines: list[str] = []

    def add(label: str, value) -> None:
        if value not in (None, "", "–"):
            lines.append(f"- {label}: {value}")

    # Company / project identity
    try:
        add("Company", rd._company_name(project, setup))
    except Exception:
        add("Company", project.name)
    if setup:
        add("Project", setup.project_name or project.name)
        add("Industry", setup.industry)
        add("Business model", setup.business_model.value.replace("_", " ") if setup.business_model else None)
        add("Location", ", ".join(filter(None, [setup.city, setup.country])) or None)
        add("Currency", setup.currency)
        add("Business description", setup.business_description)
        if setup.projection_period:
            add("Projection horizon", f"{setup.projection_period.years} years")
    else:
        add("Project", project.name)

    # Selected scenario
    scenario = _default_scenario(project)
    scenario_id = "base"
    if scenario is not None:
        add("Selected scenario", scenario.name or scenario.label or scenario.scenario_type.value)
        scenario_id = scenario.id

    # Revenue streams (products)
    active_products = [p for p in project.products if getattr(p, "active", True)]
    if active_products:
        lines.append(f"- Revenue streams ({len(active_products)}):")
        for p in active_products[:12]:
            bits = [p.name]
            if p.selling_price:
                bits.append(f"price {p.selling_price:,.0f} {setup.currency if setup else ''}".strip())
            rtype = getattr(p.revenue_type, "value", None)
            if rtype:
                bits.append(rtype.replace("_", " "))
            lines.append(f"    • {' — '.join(bits)}")

    # Direct costs (names only — no need to recompute)
    active_costs = [c for c in project.direct_costs if getattr(c, "active", True)]
    if active_costs:
        names = ", ".join(c.name for c in active_costs[:10])
        add("Direct cost items", names)

    # Revenue projection + income statement highlights (read-only compute)
    try:
        from . import income_statement_service as isvc

        summary = isvc.build_summary(project, scenario_id)
        cur = summary.currency or (setup.currency if setup else "")
        add("Total projected revenue", f"{summary.total_revenue:,.0f} {cur}".strip())
        add("Gross profit", f"{summary.gross_profit:,.0f} {cur}".strip())
        add("EBITDA", f"{summary.ebitda:,.0f} {cur}".strip())
        add("Net profit", f"{summary.net_profit:,.0f} {cur}".strip())
        add("Gross margin", f"{summary.gross_margin:.1f}%")
        add("Net profit margin", f"{summary.net_profit_margin:.1f}%")
    except Exception:
        logger.debug("Income statement summary unavailable for AI context", exc_info=True)

    return "\n".join(lines)


# --------------------------------------------------------------------------
# prompt assembly
# --------------------------------------------------------------------------
_TONE_GUIDANCE = {
    "investor": "Persuasive and growth-oriented, aimed at prospective investors; "
                "emphasise opportunity, traction and returns while staying credible.",
    "bank": "Conservative and risk-aware, aimed at a lending bank; emphasise "
            "repayment capacity, stability and downside protection.",
    "formal": "Formal, professional business-plan prose.",
    "government": "Formal tone suitable for a government body or grant authority; "
                  "emphasise compliance, economic impact and job creation.",
    "simple": "Plain, simple language that a non-specialist reader can follow.",
    "big_four": "Polished, structured, advisory tone in the style of a Big Four "
                "consulting firm; precise, evidence-led and well organised.",
}

_ACTION_INSTRUCTION = {
    "generate": "Write a new, well-structured narrative for this section.",
    "improve": "Improve the clarity, flow and professionalism of the text below "
               "without inventing facts.",
    "shorten": "Make the text below more concise while preserving its key points.",
    "expand": "Expand the text below with more depth and detail, staying consistent "
              "with the facts given.",
    "translate_arabic": "Translate the text below into professional Modern Standard Arabic.",
    "translate_english": "Translate the text below into professional English.",
}


def build_prompt(request: AiGenerateRequest, context: str) -> tuple[str, str]:
    """Return (system_prompt, user_prompt)."""
    language = "Arabic" if request.language == "arabic" else "English"
    if request.action == "translate_arabic":
        language = "Arabic"
    elif request.action == "translate_english":
        language = "English"

    tone = _TONE_GUIDANCE.get(request.tone, _TONE_GUIDANCE["formal"])
    section = request.section_title or request.section_key or "this section"

    system = (
        "You are an expert business-plan writer helping to draft the narrative "
        "sections of a professional business plan. Write clear, credible, "
        f"well-structured prose. Output language: {language}. Tone: {tone} "
        "Return only the narrative content itself — no preamble, no markdown "
        "code fences, no meta commentary."
    )

    parts: list[str] = [f"Section: {section}", f"Task: {_ACTION_INSTRUCTION[request.action]}"]
    if request.user_prompt.strip():
        parts.append(f"Additional instructions: {request.user_prompt.strip()}")
    if context:
        parts.append("Project context (facts you may use — do not contradict them):\n" + context)
    if (request.current_text or "").strip():
        parts.append("Existing text:\n" + request.current_text.strip())

    return system, "\n\n".join(parts)


# --------------------------------------------------------------------------
# provider calls (HTTP via stdlib — no extra dependency)
# --------------------------------------------------------------------------
def _ssl_context() -> ssl.SSLContext | None:
    """SSL context for outbound AI calls.

    Honours a custom CA bundle, or (local dev only) disables verification for
    networks doing HTTPS inspection. Returns None to use urllib's default.
    """
    if settings.ai_ca_bundle:
        return ssl.create_default_context(cafile=settings.ai_ca_bundle)
    if not settings.ai_verify_ssl:
        logger.warning("AI_SSL_VERIFY=false: outbound AI TLS verification is DISABLED "
                       "(intended for local dev behind HTTPS inspection only).")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


def _http_post_json(url: str, headers: dict, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=settings.ai_timeout_seconds,
                                    context=_ssl_context()) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")[:500]
        except Exception:
            pass
        raise AiProviderError(f"AI provider returned HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise AiProviderError(f"Could not reach the AI provider: {exc.reason}") from exc


def _call_provider(cfg: ProviderConfig, system: str, user: str) -> str:
    """Dispatch to the configured provider and return the generated text.

    Tests monkeypatch this function to avoid real network calls.
    """
    if cfg.provider == "openai":
        result = _http_post_json(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
            {
                "model": cfg.model,
                "max_tokens": settings.ai_max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        try:
            return result["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise AiProviderError("Unexpected response from OpenAI.") from exc

    # anthropic
    result = _http_post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": cfg.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        {
            "model": cfg.model,
            "max_tokens": settings.ai_max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
    )
    try:
        return "".join(block.get("text", "") for block in result["content"]).strip()
    except (KeyError, TypeError) as exc:
        raise AiProviderError("Unexpected response from Anthropic.") from exc


# --------------------------------------------------------------------------
# entrypoint
# --------------------------------------------------------------------------
def generate(project: BusinessPlanProject, request: AiGenerateRequest) -> AiGenerateResponse:
    cfg = resolve_provider()  # raises AiNotConfiguredError → route returns 503
    context = build_context(project)
    system, user = build_prompt(request, context)
    content = _call_provider(cfg, system, user)
    if not content:
        raise AiProviderError("The AI provider returned an empty response.")
    return AiGenerateResponse(
        content=content,
        language=request.language,
        action=request.action,
        provider=cfg.provider,
        model=cfg.model,
    )
