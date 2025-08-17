## Features
**Query Builder** – Generate search queries by Market × Industry × Topic  
**Upload results** – Accepts CSV/XLSX from search/news tools (Google, Bing, SerpAPI, NewsAPI)  
**Smart scoring** – Ranks leads by ESG & Compliance keywords (+ weighting for context)  
**Contact enrichment (optional)** – Best-effort extraction of public names/emails from company pages  
**Export** – Download scored leads as CSV or Excel  

## Run locally
```bash
# Clone this repo
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

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
