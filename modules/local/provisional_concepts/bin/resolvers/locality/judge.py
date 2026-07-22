try:
    from clients.llm_client import run_llm_batch
except ImportError:
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))
    from clients.llm_client import run_llm_batch


_SYSTEM = (
    "You are an ENVO (Environment Ontology) curator deciding whether any candidate ENVO term is the SAME "
    "habitat/environment concept as a field-collected locality description. You are given the original "
    "German term, its English translation, the top ENVO retrieval candidates with their confidence scores "
    "and a habitat flag, and an upstream CORINE Land Cover (CLC) classification.\n"
    "ENVO distinguishes HABITATS / ecosystems / biomes / places (e.g. pasture, forest biome, wet meadow "
    "ecosystem) from ENVIRONMENTAL MATERIALS / substrates (e.g. pasture soil, jungle soil, fresh water, "
    "sandy loam). A material/substrate variant is almost never the correct match for a habitat phrase; "
    "prefer a true habitat/biome/ecosystem term.\n"
    "Use the candidate confidence scores and the CLC as evidence, but the German and English terms are "
    "primary — the CLC can misfire on place names.\n"
    "Return JSON: disposition = 'accept' (a candidate is the same concept — also set match to its "
    "1-based index), 'register' (the term is a genuine habitat/environment concept that is NOT in ENVO "
    "— provide definition), or 'discard' (the term is not actually an environment/habitat concept at "
    "all, e.g. a compass direction, a plant trait or description, or a pure place name that slipped "
    "through); confidence = high|medium|low; justification = why; definition = a concise definition of "
    "the concept (only for 'register'). For 'register' the justification MUST argue why the term fits "
    "in ENVO AND why the best candidate matches are wrong (name them with their scores)."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "match": {"type": ["integer", "null"]},
        "disposition": {"type": "string", "enum": ["accept", "register", "discard"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "justification": {"type": "string"},
        "definition": {"type": "string"},
    },
    "required": ["disposition", "confidence", "justification"],
}


def _candidate_line(i, c):
    label = c.get("label") or ""
    score = c.get("rerank_score", c.get("score", 0.0))
    hab = "habitat" if c.get("is_habitat") else "material/other"
    desc = c.get("description") or []
    desc = desc[0] if isinstance(desc, list) and desc else (desc or "")
    return f"{i}. {label} (score {score:.2f}, {hab}) — {desc}"


def _prompt(job):
    lines = [f"German term: {job['german']}", f"English term: {job['english']}"]
    clc = job.get("clc") or {}
    if clc.get("name"):
        lines.append(f"Upstream CLC: {clc.get('code', '')} = {clc['name']} (conf {clc.get('conf', '')})")
    lines.append("ENVO candidates:")
    lines.extend(_candidate_line(i, c) for i, c in enumerate(job["candidates"], 1))
    lines.append("Return JSON {match, confidence, justification, definition}.")
    return "\n".join(lines)


def judge_concepts(jobs):
    """Batch identity-judge over the top-K ENVO candidates. Returns a list (aligned with jobs) of
    {match, confidence, justification, definition} dicts (match is a 1-based index or None)."""
    if not jobs:
        return []
    llm_jobs = [{"prompt": _prompt(j), "system": _SYSTEM, "schema": _SCHEMA} for j in jobs]
    return run_llm_batch(llm_jobs)
