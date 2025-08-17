# 2) Upload Raw Results (CSV or Excel)
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
    comp_list = [x.strip() for x in compliance_kw.split(",") if x.strip()]
    role_list = [x.strip() for x in esg_role_kw.split(",") if x.strip()]
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
    csv = leads_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Leads CSV", data=csv, file_name="gb2b_leads.csv", mime="text/csv")

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
        leads_df.to_excel(writer, sheet_name="leads", index=False)
        if not contacts_df.empty:
            contacts_df.to_excel(writer, sheet_name="contacts", index=False)
    towrite.seek(0)
    st.download_button("Download XLSX (leads + contacts)", data=towrite, file_name="gb2b_leads_and_contacts.xlsx")

else:
    st.info("Upload a CSV/XLSX of search results to continue. You can generate queries above.")

else:
    st.info("Upload a CSV/XLSX of search results to continue. You can generate queries above.")
