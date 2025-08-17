# --- Export ---
csv = leads_df.to_csv(index=False).encode("utf-8")
st.download_button("Download Leads CSV", data=csv, file_name="gb2b_leads.csv", mime="text/csv")

towrite = io.BytesIO()
with pd.ExcelWriter(towrite, engine="xlsxwriter") as writer:
    leads_df.to_excel(writer, sheet_name="leads", index=False)
    if not contacts_df.empty:
        contacts_df.to_excel(writer, sheet_name="contacts", index=False)
towrite.seek(0)
st.download_button("Download XLSX (leads + contacts)", data=towrite, file_name="gb2b_leads_and_contacts.xlsx")

        leads_df = leads_df.drop_duplicates(subset=["domain","title"], keep="first")
        leads_df = leads_df.sort_values(["score"], ascending=False).reset_index(drop=True)
    st.dataframe(leads_df, use_container_width=True)

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

    st.subheader("4) Export")
    csv = leads_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Leads CSV", data=csv, file_name="gb2b_leads.csv", mime="text/csv")

    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
        leads_df.to_excel(writer, sheet_name="leads", index=False)
        if not contacts_df.empty:
            contacts_df.to_excel(writer, sheet_name="contacts", index=False)
    towrite.seek(0)
    st.download_button("Download XLSX (leads + contacts)", data=towrite, file_name="gb2b_leads_and_contacts.xlsx")

else:
    st.info("Upload a CSV/XLSX of search results to continue. You can generate queries above.")
