"""Products + Startups verticals: Product Hunt GraphQL API.
Each Product Hunt post's maker/company doubles as a Startup entity."""
import aiohttp, asyncio, csv, json, re, requests
from datetime import datetime, timezone
from llm_fallback import extract_with_fallback

PH_URL = "https://api.producthunt.com/v2/api/graphql"

PH_QUERY = """
query($cursor: String) {
  posts(first: 50, after: $cursor, order: VOTES) {
    edges { node { id name tagline description url website createdAt votesCount makers { name } } }
    pageInfo { hasNextPage endCursor }
  }
}
"""

def get_ph_token(client_id, client_secret):
    resp = requests.post("https://api.producthunt.com/v2/oauth/token", json={
        "client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"})
    return resp.json()["access_token"]

async def fetch_producthunt_posts(token, target_count=1100):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    posts, cursor = [], None
    async with aiohttp.ClientSession() as session:
        while len(posts) < target_count:
            payload = {"query": PH_QUERY, "variables": {"cursor": cursor}}
            async with session.post(PH_URL, json=payload, headers=headers) as resp:
                data = await resp.json()
                if "errors" in data:
                    print("GraphQL error:", data["errors"]); break
                page = data["data"]["posts"]
                posts.extend([e["node"] for e in page["edges"]])
                if not page["pageInfo"]["hasNextPage"]:
                    break
                cursor = page["pageInfo"]["endCursor"]
                await asyncio.sleep(1)
    return posts

def build_batch_prompt(batch):
    lines = [f"{i}: {(p.get('tagline') or '')[:80]} | {(p.get('description') or '')[:100]}"
              for i, p in enumerate(batch)]
    return ("Classify the pricing model for each product below.\n"
            "Reply ONLY one of: FREE, FREEMIUM, PAID, ENTERPRISE per item.\n\nItems:\n"
            + "\n".join(lines) +
            '\n\nRespond ONLY with valid JSON: {"0": "FREEMIUM", "1": "PAID", ...}')

def classify_batch(batch, providers):
    prompt = build_batch_prompt(batch)
    try:
        result, provider = extract_with_fallback(prompt, providers, max_retries=3)
        match = re.search(r"\{.*\}", result, re.DOTALL)
        parsed = json.loads(match.group(0)) if match else {}
    except Exception as e:
        print(f"Batch failed: {e}")
        parsed, provider = {}, "failed"
    out = []
    for i, post in enumerate(batch):
        pricing = parsed.get(str(i), "FREEMIUM").upper()
        if pricing not in ["FREE", "FREEMIUM", "PAID", "ENTERPRISE"]:
            pricing = "FREEMIUM"
        out.append((post, pricing, provider))
    return out

def build_startups(posts):
    seen, out = set(), []
    for post in posts:
        name = post.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        out.append({
            "schemaVersion": "1.0", "recordType": "STARTUP",
            "source": {"name": "ProductHunt", "url": post.get("url")},
            "content": {"entityName": name, "data": {"employeeCount": None}},  # honestly null
            "collectedAt": datetime.now(timezone.utc).isoformat(),
        })
    return out

def save_csv(rows, path, header, row_fn):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header)
        for r in rows: w.writerow(row_fn(r))
