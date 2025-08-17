# -*- coding: utf-8 -*-
# GB2B Lead Harvester: auto-find + auto-populate leads into CSV/XLSX

import os, time, re, io
from urllib.parse import urlparse
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ---- EDIT FOR YOUR FOCUS ----
MARKETS    = ["India", "UAE", "Vietnam", "European Union", "Singapore", "UK"]
INDUSTRIES = ["manufacturing", "pharmaceuticals", "FMCG", "energy", "real estate", "consumer brands", "exporters"]
TOPICS     = ["BRSR", "CSRD", "Scope 3", "carbon credits", "sustainability report", "ESG strategy", "assurance"]

ENABLE_CONTACTS        = False   # set True later if needed (slower)
MAX_PAGES_PER_DOMAIN   = 3
PER_DOMAIN_DELAY_SEC   = 2.0

COMPLIANCE_KEYWORDS = [
    "BRSR","SEBI","CSRD","SEC climate","IFRS S1","IFRS S2",
    "Scope 1","Scope 2","Scope 3","TCFD","CDP","ESG rating",
    "assurance","materiality","double materiality","carbon credits",
    "offsets","RECs","renewable energy certificate","energy attribute certificates"
]
ESG_ROLE_KEYWORDS = [
    "Head of Sustainability","Chief Sustainability Officer","CSO",
    "ESG Lead","ESG Manager","Sustainability Manager","ESG Director"
]

DEFAULT_HEADERS = {
    "User-Agent": os.getenv("LF_UA", "GB2B-LeadHarvester/1.0"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def parse_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""

def safe_get(url, timeout=15):
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type",""):
            return r.text
    except Exception:
        return None
    return None

def score_row(text, market=None, industry=None, published_at=None):
    score = 0
    text_l = (text or "").lower()
    hits = []
    for k in (TOPICS + COMPLIANCE_KEYWORDS + ESG_ROLE_KEYWORDS):
        if k.lower() in text_l:
            hits.append(k)
    hits = sorted(set(hits))
    score += len(hits) * 2
    comp_hits = [k for k in hits if k in COMPLIANCE_KEYWORDS]
    score += len(comp_hits) * 3
    if market: score += 2
    if industry: score += 2
    if published_at: score += 1
    return score, hits

def serpapi_web_search(q, api_key, num=10):
    url = "https://serpapi.com/search.json"
    params = {"q": q, "hl": "en", "num": num, "engine": "google", "api_key": api_key}
    r = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    out = []
    for item in (data.get("organic_results") or []):
        out.append({"title": item.get("title"), "url": item.get("link"),
                    "snippet": item.get("snippet"), "source": "serpapi",
                    "published_at": None})
    return out

def bing_web_search(q, api_key, endpoint, count=10):
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": q, "count": count}
    r = requests.get(endpoint, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    out = []
    for item in (data.get("webPages", {}).get("value") or []):
        out.append({"title": item.get("name"), "url": item.get("url"),
                    "snippet": item.get("snippet"), "source": "bing",
                    "published_at": None})
    return out

def newsapi_search(q, api_key, page_size=20):
    url = "https://newsapi.org/v2/everything"
    params = {"q": q, "pageSize": page_size, "sortBy": "publishedAt",
              "apiKey": api_key, "language": "en"}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    out = []
    for a in (data.get("articles") or []):
        out.append({"title": a.get("title"), "url": a.get("url"),
                    "snippet": a.get("description"), "source": "newsapi",
                    "published_at": (a.get("publishedAt") or None)})
    return out

def extract_contacts_from_domain(domain, max_pages=3, delay=2.0):
    homepage = f"https://{domain}"
    html = safe_get(homepage)
    if not html: return []
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    candidates, seen, pages = [], set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/"): href = f"https://{domain}{href}"
        if domain in href and any(seg in href.lower() for seg in
            ["sustainability","esg","about","leadership","team","contact","governance","board","investor"]):
            if href not in seen:
                candidates.append(href); seen.add(href)
    for c in candidates:
        if len(pages) >= max_pages: break
        pages.append(c)
    results = []
    for p in pages:
        time.sleep(delay)
        content = safe_get(p)
        if not content: continue
        emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", content))
        for e in emails:
            results.append({"page": p, "name": None, "title": None, "email": e})
        for m in re.finditer(
            r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,3}).{0,60}(Sustainability|ESG|CSR|Environment|Climate)\s?(Head|Lead|Manager|Director|Officer)?",
            content):
            name = m.group(1).strip()
            title = " ".join([t for t in m.groups()[1:] if t]).strip()
            results.append({"page": p, "name": name, "title": title, "email": None})
    unique = {(r["name"], r["title"], r["email"], r["page"]) for r in results}
    return [dict(name=n, title=t, email=e, page=pg) for (n,t,e,pg) in unique]

def main():
    serp_key = os.getenv("SERPAPI_KEY","").strip()
    bing_key = os.getenv("BING_API_KEY","").strip()
    bing_endpoint = os.getenv("BING_ENDPOINT","https://api.bing.microsoft.com/v7.0/search").strip()
    news_key = os.getenv("NEWSAPI_KEY","").strip()

    provider = "serpapi" if serp_key else ("bing" if bing_key else None)
    if not provider and not news_key:
        print("[INFO] No SERPAPI_KEY/BING_API_KEY/NEWSAPI_KEY set. Exiting.")
        return

    LIMIT = 10
    rows = []
    for m in MARKETS:
        for i in INDUSTRIES:
            for t in TOPICS:
                query = f'{t} "{i}" site:newsroom OR "sustainability report" "{m}"'
                results = []
                try:
                    if provider == "serpapi":
                        results = serpapi_web_search(query, serp_key, num=LIMIT)
                    elif provider == "bing":
                        results = bing_web_search(query, bing_key, bing_endpoint, count=LIMIT)
                except Exception as e:
                    print(f"[WARN] Web search error for '{query}': {e}")
                for r in results:
                    url = r.get("url","")
                    title = r.get("title","") or ""
                    snippet = r.get("snippet","") or ""
                    text = f"{title} {snippet}"
                    sc, hits = score_row(text, m, i, r.get("published_at"))
                    domain = parse_domain(url)
                    company = (domain.split(".")[0].capitalize() if domain else None)
                    rows.append({
                        "company": company, "domain": domain, "url": url,
                        "title": title, "snippet": snippet,
                        "market": m, "industry": i, "topic": t,
                        "keywords_matched": ", ".join(hits),
                        "source": r.get("source"), "published_at": r.get("published_at"),
                        "score": sc
                    })
                if news_key:
                    nq = f'{t} {i} {m}'
                    try:
                        news = newsapi_search(nq, news_key, page_size=LIMIT)
                    except Exception as e:
                        print(f"[WARN] NewsAPI error for '{nq}': {e}")
                        news = []
                    for n in news:
                        url = n.get("url","")
                        title = n.get("title","") or ""
                        snippet = n.get("snippet","") or ""
                        text = f"{title} {snippet}"
                        sc, hits = score_row(text, m, i, n.get("published_at"))
                        domain = parse_domain(url)
                        company = (domain.split(".")[0].capitalize() if domain else None)
                        rows.append({
                            "company": company, "domain": domain, "url": url,
                            "title": title, "snippet": snippet,
                            "market": m, "industry": i, "topic": t,
                            "keywords_matched": ", ".join(hits),
                            "source": n.get("source"), "published_at": n.get("published_at"),
                            "score": sc
                        })
    if not rows:
        print("[INFO] No rows found.")
        return

    df = pd.DataFrame(rows).drop_duplicates(subset=["domain","title"], keep="first")
    df = df.sort_values(["score"], ascending=False).reset_index(drop=True)

    contacts_df = pd.DataFrame(columns=["domain","name","title","email","page"])
    if ENABLE_CONTACTS:
        print("[INFO] Extracting public contacts…")
        contacts = []
        for d in df["domain"].dropna().unique().tolist()[:30]:
            ppl = extract_contacts_from_domain(d, max_pages=MAX_PAGES_PER_DOMAIN, delay=PER_DOMAIN_DELAY_SEC)
            for p in ppl:
                contacts.append({"domain": d, **p})
        if contacts:
            contacts_df = pd.DataFrame(contacts).drop_duplicates()

    df_out = df[[
        "company","domain","market","industry","title","snippet","score",
        "url","keywords_matched","published_at","topic","source"
    ]]
    df_out.to_csv("gb2b_leads.csv", index=False, encoding="utf-8")
    with pd.ExcelWriter("gb2b_leads.xlsx", engine="xlsxwriter") as w:
        df_out.to_excel(w, sheet_name="leads", index=False)
        if not contacts_df.empty:
            contacts_df.to_excel(w, sheet_name="contacts", index=False)
    print(f"[OK] Wrote {len(df_out)} leads to gb2b_leads.csv and gb2b_leads.xlsx")

if __name__ == "__main__":
    main()
