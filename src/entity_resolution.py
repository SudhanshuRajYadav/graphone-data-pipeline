"""Deterministic entity resolution: fuzzy-matches raw startup names against a
seed list of 50 known canonical AI startups."""
from rapidfuzz import process, fuzz
import csv

CANONICAL_STARTUPS = {
    "OpenAI": ["OpenAI Inc", "Open AI", "OpenAI LP"],
    "Anthropic": ["Anthropic PBC", "Anthropic AI"],
    "Google DeepMind": ["DeepMind", "Google Deepmind"],
    "Microsoft": ["Microsoft Corp", "MSFT"],
    "Meta": ["Meta Platforms", "Facebook AI"],
    "Amazon": ["Amazon.com", "AWS"],
    "Nvidia": ["NVIDIA Corporation"],
    "Perplexity": ["Perplexity AI", "Perplexity.ai"],
    "Mistral AI": ["Mistral", "Mistral.ai"],
    "Cohere": ["Cohere Inc"],
    "Stability AI": ["StabilityAI", "Stability"],
    "Hugging Face": ["HuggingFace", "Hugging Face Inc"],
    "Scale AI": ["Scale", "ScaleAI"],
    "Runway": ["Runway ML", "RunwayML"],
    "Character.AI": ["CharacterAI", "Character AI"],
    "Inflection AI": ["Inflection"],
    "Adept": ["Adept AI"],
    "Cursor": ["Cursor AI", "Anysphere"],
    "Replit": ["Replit Inc"],
    "Vercel": ["Vercel Inc"],
    "Notion": ["Notion Labs"],
    "Figma": ["Figma Inc"],
    "Canva": ["Canva Pty"],
    "Airtable": ["Airtable Inc"],
    "Zapier": ["Zapier Inc"],
    "Linear": ["Linear App"],
    "Retool": ["Retool Inc"],
    "Supabase": ["Supabase Inc"],
    "Together AI": ["TogetherAI", "Together Compute"],
    "Groq": ["Groq Inc"],
    "xAI": ["X.AI", "xAI Corp"],
    "Midjourney": ["Midjourney Inc"],
    "ElevenLabs": ["Eleven Labs"],
    "Pinecone": ["Pinecone Systems"],
    "Weights & Biases": ["WandB", "Weights and Biases"],
    "LangChain": ["Langchain Inc"],
    "Databricks": ["Databricks Inc"],
    "Snowflake": ["Snowflake Inc"],
    "Palantir": ["Palantir Technologies"],
    "C3.ai": ["C3 AI", "C3.ai Inc"],
    "UiPath": ["UiPath Inc"],
    "Glean": ["Glean Technologies"],
    "Sierra": ["Sierra AI"],
    "Harvey": ["Harvey AI"],
    "Cognition": ["Cognition Labs", "Devin AI"],
    "Vanta": ["Vanta Inc"],
    "Ramp": ["Ramp Inc"],
    "Brex": ["Brex Inc"],
    "Deel": ["Deel Inc"],
    "Rippling": ["Rippling Inc"],
}

_alias_to_canonical, _all_terms = {}, []
for canon, aliases in CANONICAL_STARTUPS.items():
    _alias_to_canonical[canon.lower()] = canon
    _all_terms.append(canon)
    for a in aliases:
        _alias_to_canonical[a.lower()] = canon
        _all_terms.append(a)

def resolve_entity(raw_name, threshold=85):
    if not raw_name:
        return None, 0
    key = raw_name.strip().lower()
    if key in _alias_to_canonical:
        return _alias_to_canonical[key], 100
    match = process.extractOne(raw_name, _all_terms, scorer=fuzz.WRatio)
    if match and match[1] >= threshold:
        term, score, _ = match
        return _alias_to_canonical[term.lower()], score
    return None, 0  # left unresolved rather than force-matched

def resolve_all(startups_data, out_path="entity_mapping_log.csv"):
    log = []
    for s in startups_data:
        raw = s["content"]["entityName"]
        canonical, score = resolve_entity(raw)
        log.append({"raw_name": raw, "canonical_name": canonical or raw,
                     "matched_known_entity": bool(canonical), "confidence": score})
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["raw_name", "canonical_name", "matched_known_entity", "confidence"])
        for e in log:
            w.writerow([e["raw_name"], e["canonical_name"], e["matched_known_entity"], e["confidence"]])
    return log
