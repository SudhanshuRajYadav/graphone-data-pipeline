"""Jobs + News verticals. Uses structured APIs/RSS (with real publish timestamps)
instead of scraping + heuristic date parsing, wherever available."""
import requests, csv, feedparser
from datetime import datetime, timezone, timedelta

def classify_role_family(title):
    title = (title or "").lower()
    if any(k in title for k in ["engineer", "developer", "swe", "backend", "frontend", "fullstack"]):
        return "Engineering"
    if any(k in title for k in ["data scientist", "data analyst", "ml engineer", "machine learning"]):
        return "Data/ML"
    if any(k in title for k in ["design", "ux", "ui"]):
        return "Design"
    if any(k in title for k in ["sales", "account exec", "business development"]):
        return "Sales"
    if any(k in title for k in ["market", "growth", "seo"]):
        return "Marketing"
    if any(k in title for k in ["product manager", "product owner"]):
        return "Product"
    return "Other"

def fetch_jobs(now=None):
    now = now or datetime.now(timezone.utc)
    jobs = []

    # Source 1: RemoteOK
    try:
        raw = requests.get("https://remoteok.com/api", headers={"User-Agent": "Mozilla/5.0"}).json()[1:]
        for j in raw:
            d = j.get("date")
            if not d:
                continue
            jd = datetime.fromisoformat(d.replace("Z", "+00:00"))
            if (now - jd) <= timedelta(hours=24):
                jobs.append(_job_record("RemoteOK", j.get("company"), jd, True,
                                          classify_role_family(j.get("position")), j.get("url"), now))
    except Exception as e:
        print("RemoteOK failed:", e)

    # Source 2: Arbeitnow
    try:
        raw = requests.get("https://www.arbeitnow.com/api/job-board-api",
                            headers={"User-Agent": "Mozilla/5.0"}).json().get("data", [])
        for j in raw:
            ts = j.get("created_at")
            if not ts:
                continue
            jd = datetime.fromtimestamp(ts, tz=timezone.utc)
            if (now - jd) <= timedelta(hours=24):
                jobs.append(_job_record("Arbeitnow", j.get("company_name"), jd, j.get("remote", False),
                                          classify_role_family(j.get("title")), j.get("url"), now))
    except Exception as e:
        print("Arbeitnow failed:", e)

    return jobs

def _job_record(source, company, date, remote, role_family, url, now):
    return {"schemaVersion": "1.0", "recordType": "JOB",
            "source": {"name": source, "url": url},
            "content": {"company": company, "date": date.isoformat(),
                        "is_remote": remote, "role_family": role_family},
            "collectedAt": now.isoformat()}

RSS_FEEDS = {
    "TechCrunch": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat": "https://venturebeat.com/category/ai/feed/",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
}

def fetch_news(now=None):
    now = now or datetime.now(timezone.utc)
    news = []
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if not pub:
                    continue
                pub_date = datetime(*pub[:6], tzinfo=timezone.utc)
                if (now - pub_date) > timedelta(hours=24):
                    continue
                news.append({
                    "schemaVersion": "1.0", "recordType": "NEWS",
                    "source": {"name": source_name, "url": entry.get("link")},
                    "content": {"title": entry.get("title"), "published_date": pub_date.isoformat(),
                                 "summary": (entry.get("summary") or "")[:300]},
                    "collectedAt": now.isoformat(),
                })
        except Exception as e:
            print(f"{source_name} failed: {e}")
    return news

def save_csv(rows, path, header, row_fn):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header)
        for r in rows: w.writerow(row_fn(r))
