"""Research Papers vertical: HuggingFace paper<->code dataset + arXiv API + GitHub API.
No scraping needed — uses official/public data sources only."""
import aiohttp, asyncio, re, csv
from xml.etree import ElementTree as ET
from datetime import datetime, timezone
from datasets import load_dataset

GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"

SEM_ARXIV = asyncio.Semaphore(3)
SEM_GITHUB = asyncio.Semaphore(8)

async def fetch_arxiv_meta(session, arxiv_id):
    if not arxiv_id:
        return {}
    url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
    async with SEM_ARXIV:
        try:
            async with session.get(url) as resp:
                text = await resp.text()
            await asyncio.sleep(0.5)
            root = ET.fromstring(text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entry = root.find("atom:entry", ns)
            title = entry.find("atom:title", ns).text.strip()
            authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)]
            published = entry.find("atom:published", ns).text
            return {"title": title, "authors": authors, "published_date": published}
        except Exception:
            return {}

async def fetch_github_stars(session, repo_url):
    m = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url or "")
    if not m:
        return None
    owner, repo = m.group(1), m.group(2).rstrip("/")
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    async with SEM_GITHUB:
        try:
            async with session.get(api_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("stargazers_count")
                elif resp.status == 403:
                    await asyncio.sleep(60)  # secondary rate limit cooldown
                return None
        except Exception:
            return None

async def process_paper(session, row):
    meta = await fetch_arxiv_meta(session, row.get("paper_arxiv_id"))
    stars = await fetch_github_stars(session, row.get("repo_url"))
    return {
        "schemaVersion": "1.0", "recordType": "RESEARCH_PAPER",
        "content": {
            "title": meta.get("title") or row.get("paper_title"),
            "authors": meta.get("authors", []),
            "paper_url": row.get("paper_url_abs") or row.get("paper_url"),
            "github_url": row.get("repo_url"),
            "github_stars": stars,
            "published_date": meta.get("published_date"),
        },
        "source": {"name": "arXiv/PapersWithCode", "url": row.get("paper_url")},
        "collectedAt": datetime.now(timezone.utc).isoformat(),
    }

async def run_papers_pipeline(target_count=1200):
    ds = load_dataset("pwc-archive/links-between-paper-and-code", split="train")
    rows = [r for r in ds if r.get("repo_url")][:target_count]
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [process_paper(session, r) for r in rows]
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            try:
                results.append(await coro)
            except Exception as e:
                print(f"Failed: {e}")
            if (i + 1) % 50 == 0:
                print(f"{i+1}/{len(tasks)} done")
    return results

def save_papers_csv(papers, path="research_papers.csv"):
    seen = set()
    unique = [p for p in papers if p["content"]["paper_url"]
              and not (p["content"]["paper_url"] in seen or seen.add(p["content"]["paper_url"]))]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["title", "authors", "paper_url", "github_url", "github_stars",
                     "published_date", "source_url", "collectedAt"])
        for p in unique:
            c = p["content"]
            w.writerow([c["title"], "; ".join(c["authors"]), c["paper_url"], c["github_url"],
                        c["github_stars"], c["published_date"], p["source"]["url"], p["collectedAt"]])
    return unique

if __name__ == "__main__":
    papers = asyncio.run(run_papers_pipeline())
    save_papers_csv(papers)
