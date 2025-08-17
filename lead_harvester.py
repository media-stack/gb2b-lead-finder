#!/usr/bin/env python3
import os, io, time, re, json, requests
import pandas as pd

# ---- EDIT FOR YOUR FOCUS ----
MARKETS = [
    "EU (Germany)", "EU (France)", "EU (Netherlands)", "EU (Nordics)", "EU (Spain)", "EU (Italy)",
    "UK", "Australia", "Singapore", "Hong Kong", "Japan", "India",
    "United States (California)", "UAE", "Saudi Arabia"
]

INDUSTRIES = [
    "financial services","banks","asset management","insurance",
    "energy","utilities","oil & gas",
    "chemicals","cement","steel","mining",
    "automotive","transport","logistics","aviation","shipping",
    "consumer goods","retail","FMCG",
    "real estate","REITs","construction",
    "technology","electronics","healthcare","pharma"
]

TOPICS = [
    "CSRD","ESRS","double materiality",
    "IFRS S2","IFRS S1","ISSB","transition plan",
    "Scope 1","Scope 2","Scope 3",
    "assurance","limited assurance","reasonable assurance",
    "TCFD","CDP","EU Taxonomy","CBAM",
    "California SB253","SB261",
    "BRSR","BRSR Core","SEBI",
    "SGX climate reporting","HKEX climate disclosure","SSBJ"
]

# --- Keyword libraries for scoring ---
COMPLIANCE_KEYWORDS = [
    "BRSR","BRSR Core","SEBI",
    "CSRD","ESRS","EU Taxonomy","CBAM",
    "SEC climate","California SB253","SB261",
    "IFRS S1","IFRS S2","ISSB","SSBJ",
    "Scope 1","Scope 2","Scope 3","TCFD","CDP","ESG rating",
    "assurance","limited assurance","reasonable assurance",
    "materiality","double materiality","carbon credits",
    "offsets","RECs","renewable energy certificate","energy attribute certificates"
]

ESG_ROLE_KEYWORDS = [
    "Head of Sustainability","Chief Sustainability Officer","CSO",
    "ESG Lead","ESG Manager","Sustainability Manager","ESG Director"
]

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
    if market:
        score += 2
    if industry:
        score += 2
    if published_at:
        score += 1
    return score, hits

# --- simple web/news helpers (minimal) ---
def serpapi_web_search(q, api_key, num=10):
    url = "https://serpapi.com/search.json"
    params = {"q": q, "engine": "google", "num": num, "hl": "en", "api_key": api_key}
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    out = []
    for it in data.get("organic_results") or []:
        out.append({
            "title": it.get("title"),
            "url": it.get("link"),
            "snippet": it.get("snippet"),
            "source": "serpapi",
            "published_at": None,
        })
    return out

def bing_web_search(q, api_key, endpoint="https://api.bing.microsoft.com/v7.0/search", count=10):
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": q, "count": count}
    r = requests.get(endpoint, headers=headers, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    out = []
    for it in (data.get("webPages", {}) or {}).get("value", []):
        out.append({
            "title": it.get("name"),
            "url": it.get("url"),
            "snippet": it.get("snippet"),
            "source": "bing",
            "published_at": None,
        })
    return out

def newsapi_search(q, api_key, page_size=20):
    url = "https://newsapi.org/v2/everything"
    params = {"q": q, "pageSize": page_size, "sortBy": "publishedAt", "language": "en", "apiKey": api_key}
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    out = []
    for a in data.get("articles") or []:
        out.append({
            "title": a.get("title"),
            "url": a.get("url"),
            "snippet": a.get("description"),
            "source": "newsapi",
            "published_at": a.get("publishedAt"),
        })
    return out

def main():
    serp = os.getenv("SERPAPI_KEY")
    bing = os.getenv("BING_API_KEY")
    news = os.getenv("NEWSAPI_KEY")
    LIMIT = int(os.getenv("GB2B_LIMIT", "8"))

    rows = []

    def add_results(results, m, i, t):
        for r in results:
            title = r.get("title") or ""
            snippet = r.get("snippet") or ""
            url = r.get("url")
            published_at = r.get("published_at")
            sc, hits = score_row(f"{title} {snippet}", market=m, industry=i, published_at=published_at)
            rows.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": r.get("source"),
                "published_at": published_at,
                "market": m,
                "industry": i,
                "topic": t,
                "score": sc,
                "keywords_matched": ", ".join(hits)
            })

    # keep API usage sane: sample a small subset of combinations
    max_combos = 10
    combos = []
    for m in MARKETS:
        for i in INDUSTRIES[:3]:
            for t in TOPICS[:3]:
                combos.append((m, i, t))
                if len(combos) >= max_combos:
                    break
            if len(combos) >= max_combos:
                break
        if len(combos) >= max_combos:
            break

    for (m, i, t) in combos:
        q = f'{t} "{i}" "{m}" ("sustainability report" OR "IFRS S2" OR ESRS OR assurance)'
        try:
            if serp:
                add_results(serpapi_web_search(q, serp, num=LIMIT), m, i, t)
            elif bing:
                add_results(bing_web_search(q, bing, count=LIMIT), m, i, t)
        except Exception as e:
            print(f"[WARN] Web search error for '{q}': {e}")

        if news:
            try:
                add_results(newsapi_search(f"{t} {i} {m}", news, page_size=LIMIT), m, i, t)
            except Exception as e:
                print(f"[WARN] NewsAPI error for '{t} {i} {m}': {e}")

    # Build dataframe and write outputs
    core_cols = ["title","url","snippet","source","published_at","market","industry","topic"]
    if rows:
        df_out = pd.DataFrame(rows)
        # ensure core columns exist even if some results missing fields
        for c in core_cols:
            if c not in df_out.columns:
                df_out[c] = None
        df_out = df_out[core_cols + [c for c in df_out.columns if c not in core_cols]]
    else:
        df_out = pd.DataFrame(columns=core_cols)
        print("[INFO] No rows found; writing empty CSV with headers.")

    df_out.to_csv("gb2b_leads.csv", index=False, encoding="utf-8")
    try:
        import xlsxwriter
        df_out.to_excel("gb2b_leads.xlsx", index=False, engine="xlsxwriter")
    except Exception:
        pass
    print(f"[OK] Wrote {len(df_out)} rows to gb2b_leads.csv")

if __name__ == "__main__":
    main()
