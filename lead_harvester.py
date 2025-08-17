#!/usr/bin/env python3
"""
GB2B Lead Harvester
Auto-extracts & enriches ESG advisory leads from multiple APIs (Apollo, Lusha, SerpAPI, NewsAPI).
"""

import os, io, time, re, json, requests
import pandas as pd
from datetime import datetime

# ========== CONFIG ==========
# Buyer personas / markets / industries
MARKETS = [
    "Global Banking", "Manufacturing", "Textiles",
    "Pharmaceuticals", "Energy", "Technology"
]

INDUSTRIES = [
    "Banking", "Manufacturing", "Textile", "Pharmaceutical",
    "Automotive", "Chemicals", "Oil & Gas", "Renewable Energy"
]

BUYER_PERSONAS = [
    "Chief Sustainability Officer",
    "Head of ESG",
    "Head of Corporate Reporting",
    "Head of Risk & Compliance",
    "Chief Financial Officer",
    "Sustainability Manager",
    "Procurement Director"
]

OUTPUT_FILE = "gb2b_leads.csv"

# ========== API KEYS ==========
APOLLO_KEY = os.getenv("APOLLO_API_KEY", "")
LUSHA_KEY = os.getenv("LUSHA_API_KEY", "")
NEWS_KEY = os.getenv("NEWSAPI_KEY", "")
SERP_KEY = os.getenv("SERPAPI_KEY", "")

# ========== API HELPERS ==========

def fetch_apollo_leads(query="sustainability"):
    """Fetch sample leads from Apollo API."""
    if not APOLLO_KEY:
        print("[WARN] Apollo API key not found.")
        return []
    url = "https://api.apollo.io/v1/mixed_people/search"
    headers = {"Authorization": f"Bearer {APOLLO_KEY}"}
    payload = {"q_keywords": query, "page": 1}
    try:
        r = requests.post(url, json=payload, headers=headers)
        if r.status_code == 200:
            data = r.json()
            return [
                {
                    "name": p.get("name"),
                    "title": p.get("title"),
                    "company": p.get("organization", {}).get("name"),
                    "email": p.get("email"),
                    "source": "Apollo"
                }
                for p in data.get("people", [])
            ]
        else:
            print("[ERROR] Apollo:", r.text)
    except Exception as e:
        print("[ERROR] Apollo exception:", e)
    return []


def fetch_lusha_leads(domain="example.com"):
    """Fetch enrichment data from Lusha."""
    if not LUSHA_KEY:
        print("[WARN] Lusha API key not found.")
        return []
    url = "https://api.lusha.co/enrich/company"
    headers = {"Authorization": f"{LUSHA_KEY}"}
    params = {"domain": domain}
    try:
        r = requests.get(url, headers=headers, params=params)
        if r.status_code == 200:
            data = r.json()
            return [{
                "company": data.get("company", {}).get("name"),
                "domain": domain,
                "phone": data.get("company", {}).get("phone"),
                "source": "Lusha"
            }]
        else:
            print("[ERROR] Lusha:", r.text)
    except Exception as e:
        print("[ERROR] Lusha exception:", e)
    return []


def fetch_news_leads(keyword="ESG"):
    """Pull companies mentioned in ESG-related news."""
    if not NEWS_KEY:
        print("[WARN] NewsAPI key not found.")
        return []
    url = f"https://newsapi.org/v2/everything?q={keyword}&apiKey={NEWS_KEY}"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            return [
                {
                    "title": a.get("title"),
                    "url": a.get("url"),
                    "publishedAt": a.get("publishedAt"),
                    "source": "NewsAPI"
                }
                for a in data.get("articles", [])
            ]
        else:
            print("[ERROR] NewsAPI:", r.text)
    except Exception as e:
        print("[ERROR] NewsAPI exception:", e)
    return []


def fetch_serp_leads(query="sustainability consulting"):
    """Search results from SerpAPI."""
    if not SERP_KEY:
        print("[WARN] SerpAPI key not found.")
        return []
    url = "https://serpapi.com/search"
    params = {"engine": "google", "q": query, "api_key": SERP_KEY}
    try:
        r = requests.get(url, params=params)
        if r.status_code == 200:
            data = r.json()
            results = data.get("organic_results", [])
            return [
                {
                    "title": r.get("title"),
                    "url": r.get("link"),
                    "snippet": r.get("snippet"),
                    "source": "SerpAPI"
                }
                for r in results
            ]
        else:
            print("[ERROR] SerpAPI:", r.text)
    except Exception as e:
        print("[ERROR] SerpAPI exception:", e)
    return []


# ========== MAIN ==========

def harvest_all():
    leads = []
    print("[INFO] Fetching Apollo leads…")
    leads.extend(fetch_apollo_leads("sustainability ESG"))

    print("[INFO] Fetching Lusha leads…")
    leads.extend(fetch_lusha_leads("deloitte.com"))

    print("[INFO] Fetching News leads…")
    leads.extend(fetch_news_leads("sustainability reporting"))

    print("[INFO] Fetching SerpAPI leads…")
    leads.extend(fetch_serp_leads("ESG advisory firms"))

    # Convert to DataFrame
    if leads:
        df = pd.DataFrame(leads)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"[OK] Wrote {len(df)} leads to {OUTPUT_FILE}")
    else:
        print("[WARN] No leads harvested.")


if __name__ == "__main__":
    harvest_all()
