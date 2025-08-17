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
]# --- Keyword libraries for scoring (add below TOPICS) ---

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

df_out.to_csv("gb2b_leads.csv", index=False, encoding="utf-8")
