# -*- coding: utf-8 -*-
# GB2B Lead Finder - ESG Advisory Streamlit app (clean copy)

# (imports — you may already have these; don't duplicate)
import io, os, requests, streamlit as st

# Make the app able to pull a CSV from a URL (Streamlit secret preferred)
AUTO_CSV_URL = st.secrets.get("AUTO_CSV_URL", os.getenv("AUTO_CSV_URL", ""))
import os, re, time, io
import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import urlparse

APP_VERSION = "build-boot-ok"

# -------------------------
# Keyword libraries (editable in app)
# -------------------------
DEFAULT_COMPLIANCE = [
    "BRSR","SEBI","CSRD","SEC climate","IFRS S1","IFRS S2",
    "Scope 1","Scope 2","Scope 3","TCFD","CDP","ESG rating",
    "assurance","materiality","double materiality","carbon credits",
    "offsets","RECs","renewable energy certificate","energy attribute certificates"
]
DEFAULT_ESG_ROLES = [
    "Head of Sustainability","Chief Sustainability Officer","CSO",
    "ESG Lead","ESG Manager","Sustainability Manager","ESG Director"
]

DEFAULT_HEADERS = {
    "User-Agent": os.getenv("LF_USER_AGENT", "GB2B-LeadFinder/1.0"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# -------------------------
# Helpers
# -------------------------
def safe_get(url, timeout=15):
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type",""):
            return r.text
    except Exception:
        return None
    return None

def parse_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""

def score_row_py(row, compliance_list, esg_roles_list, topics_list):
    title = (row.get("title") or "")
    snippet = (row.get("snippet") or "")
    text = f"{title} {snippet}".lower()
    hits = set()
    for k in (topics_list + compliance_list + esg_roles_list):
        if k and k.lower() in text:
            hits.add(k)
    hits = sorted(hits)
    score = 0
    score += len(hits) * 2
    comp_hits = [k for k in hits if k in compliance_list]
    score += len(comp_hits) * 3
    if row.get("market"): score += 2
    if row.get("industry"): score += 2
    if row.get("published_at"): score += 1
    return score, hits

def extract_contacts_from_domain(domain, max_pages=3, delay=2.0):
    homepage = f"https://{domain}"
    html = safe_get(homepage)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    candidates, seen, pages = [], set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/"):
            href = f"https://{domain}{href}"
        if domain in href and any(seg in href.lower() for seg in
                                  ["sustainability","esg","about","leadership","team","contact","governance","board"]):
            if href not in seen:
                candidates.append(href)
                seen.add(href)
    for c in candidates:
        if len(pages) >= max_pages:
            break
        pages.append(c)
    results = []
    for p in pages:
        time.sleep(delay)
        content = safe_get(p)
        if not content:
            continue
        emails = set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", content))
        for e in emails:
            results.append({"page": p, "name": None, "title": None, "email": e})
        for m in re.finditer(
            r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,3}).{0,60}(Sustainability|ESG|CSR|Environment|Climate)\s?(Head|Lead|Manager|Director|Officer)?",
            content
        ):
            name = m.group(1).strip()
            title = " ".join([t for t in m.groups()[1:] if t]).strip()
            results.append({"page": p, "name": name, "title": title, "email": None})
    unique = {(r["name"], r["title"], r["email"], r["page"]) for r in results}
    return [dict(name=n, title=t, email=e, page=pg) for (n,t,e,pg) in unique]

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="GB2B Lead Finder (ESG)", layout="wide")
st.title("GB2B Lead Finder - ESG Advisory Leads")
st.caption(f"Build: {APP_VERSION}")

with st.sidebar:
    st.header("Configuration")
    with st.expander("Keyword Libraries"):
        compliance_kw = st.text_area("Compliance Keywords (comma-separated)", value=", ".join(DEFAULT_COMPLIANCE))
        esg_role_kw  = st.text_area("ESG Role Keywords (comma-separated)", value=", ".join(DEFAULT_ESG_ROLES))
    with st.expander("Markets / Industries / Topics"):
        markets_str   = st.text_input("Markets (comma-separated)", "India,UAE,Singapore,UK")
        industries_str= st.text_input("Industries (comma-separated)", "manufacturing,fintech,energy,real estate,consumer brands,exporters")
        topics_str    = st.text_input("Topics / Expertise (comma-separated)", "BRSR,CSRD,Scope 3,carbon credits,sustainability report,ESG strategy,assurance")

    st.divider()
    st.header("Optional: Contact Extraction")
    enable_contacts = st.checkbox("Extract public contacts from each domain (best-effort)", value=False)
    max_pages = st.slider("Max pages per domain", 1, 6, 3)
    delay = st.slider("Delay between page requests (secs)", 1.0, 5.0, 2.0)
    st.caption("Use responsibly. Honor site policies and legal requirements.")

# 1) Query Builder
st.subheader("1) Query Builder")
mkts = [m.strip() for m in markets_str.split(",") if m.strip()]
inds = [i.strip() for i in industries_str.split(",") if i.strip()]
tps  = [t.strip() for t in topics_str.split(",") if t.strip()]
queries = []
for m in mkts:
    for i in inds:
        for t in tps:
            q = f'{t} "{i}" site:newsroom OR "sustainability report" "{m}"'
            queries.append({"market": m, "industry": i, "topic": t, "query": q})
st.dataframe(pd.DataFrame(queries), use_container_width=True)

# 2) Upload Raw Results
st.subheader("2) Upload Raw Results (CSV or Excel)")
st.caption("Columns required: title, url, snippet, source, published_at, market, industry, topic")
file = st.file_uploader("Upload CSV/XLSX exported from your search/news tool", type=["csv","xlsx"])

if file is not None:
    raw_df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)

    expected_cols = ["title","url","snippet","source","published_at","market","industry","topic"]
    for c in expected_cols:
        if c not in raw_df.columns:
            raw_df[c] = ""

    st.success(f"Ingested {len(raw_df)} rows")
    st.dataframe(raw_df.head(25), use_container_width=True)

    # 3) Leads (scored & enriched)
    st.subheader("3) Leads (scored & enriched)")
    comp_list   = [x.strip() for x in compliance_kw.split(",") if x.strip()]
    role_list   = [x.strip() for x in esg_role_kw.split(",") if x.strip()]
    topics_list = [x.strip() for x in topics_str.split(",") if x.strip()]

    leads = []
    for _, r in raw_df.iterrows():
        url = r.get("url","")
        domain = parse_domain(url) if url else ""
        company = (domain.split(".")[0].capitalize() if domain else "")
        score, hits = score_row_py(r.to_dict(), comp_list, role_list, topics_list)
        leads.append({
            "company": company,
            "domain": domain,
            "market": r.get("market",""),
            "industry": r.get("industry",""),
            "title": r.get("title",""),
            "snippet": r.get("snippet",""),
            "score": score,
            "url": url,
            "keywords_matched": ", ".join(hits),
            "published_at": r.get("published_at",""),
            "source": r.get("source",""),
        })

    leads_df = pd.DataFrame(leads)
    if not leads_df.empty:
        leads_df = leads_df.drop_duplicates(subset=["domain","title"], keep="first")
        leads_df = leads_df.sort_values(["score"], ascending=False).reset_index(drop=True)

    st.dataframe(leads_df, use_container_width=True)

    # Optional contacts
    contacts_df = pd.DataFrame(columns=["domain","name","title","email","page"])
    if enable_contacts and not leads_df.empty:
        st.info("Extracting public contacts…")
        contacts = []
        for d in [d for d in leads_df["domain"].dropna().unique().tolist() if d][:30]:
            ppl = extract_contacts_from_domain(d, max_pages=max_pages, delay=delay)
            for p in ppl:
                contacts.append({"domain": d, **p})
        if contacts:
            contacts_df = pd.DataFrame(contacts).drop_duplicates()
            st.subheader("Public Contacts (heuristic)")
            st.dataframe(contacts_df, use_container_width=True)
        else:
            st.info("No contacts discovered on scanned pages.")

    # 4) Export
    csv_bytes = leads_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Leads CSV", data=csv_bytes, file_name="gb2b_leads.csv", mime="text/csv")

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
        leads_df.to_excel(writer, sheet_name="leads", index=False)
        if not contacts_df.empty:
            contacts_df.to_excel(writer, sheet_name="contacts", index=False)
    towrite.seek(0)
    st.download_button("Download XLSX (leads + contacts)", data=towrite, file_name="gb2b_leads_and_contacts.xlsx")

else:
    st.info("Upload a CSV/XLSX of search results to continue. You can generate queries above.")
    # --- Keyword libraries for scoring (add below TOPICS) ---
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

# (Optional) replace your score_row with this one if it differs
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

