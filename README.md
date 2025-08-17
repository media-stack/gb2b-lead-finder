# gb2b-lead-finder
GB2B Lead Finder – ESG Advisory Streamlit app
**Query Builder** – Generate search queries by Market × Industry × Topic  
**Upload results** – Accepts CSV/XLSX from search/news tools (Google, Bing, SerpAPI, NewsAPI)  
**Smart scoring** – Ranks leads by ESG & Compliance keywords (+ weighting for context)  
**Company/domain extraction** – Automatically parses domains and company names  
**Contact enrichment (optional)** – Best-effort extraction of public names/emails from company pages  
**Export** – Download scored leads as CSV or Excel (with optional contacts sheet)  
**Configurable keywords** – Compliance & ESG role keyword lists are editable in the sidebar 
## Run locally
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
pip install -r requirements.txt
streamlit run streamlit_app.py
# Create a virtual environment (optional but recommended)
python -m venv .venv
# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch the app
streamlit run streamlit_app.py
