## README

### Overview
This Python script **download_filings.py** automates fetching 10-K filings from the SEC EDGAR system for a list of US companies, preparing them for retrieval-augmented generation (RAG) workflows. You provide a CSV of tickers and date ranges; it downloads each 10-K, extracts the main text, and saves it as a JSON file with metadata.

### Requirements
- Python **3.7** or higher  
- Packages:
  ```bash
  pip install requests python-dateutil
### Input CSV Format
	•	ticker,start_date,end_date
AAPL,2020-01-01,2021-12-31
MSFT,2019-07-01,2020-06-30
	ticker: Stock symbol (e.g. AAPL)
	•	start_date, end_date: Date range in YYYY-MM-DD for the filings
### Usage
python download_filings.py companies.csv \
  --user-agent "YourName YourApp your.email@example.com"
Optional flags:
	•	--output-dir: where to store downloaded data (default data/)
	•	--mapping-file: local path for the ticker→CIK mapping JSON (default company_tickers.json)

### How It Works
	1.	Mapping: Loads or downloads SEC’s company_tickers.json to map tickers → CIKs.
	2.	Submissions Index: Queries https://data.sec.gov/submissions/CIK{CIK}.json for each company.
	3.	Filtering: Selects filings where form == "10-K" and the filingDate falls in your CSV’s date range.
	4.	Idempotency: Checks if data/<TICKER>/<ACCESSION>.json already exists; skips downloads to avoid duplicates.
	5.	Downloading: Fetches the raw text file from https://www.sec.gov/Archives/edgar/data/{CIK}/{ACCESSIONNODASH}/{ACCESSIONNODASH}.txt.
	6.	Extraction: Parses out the <TEXT> section of the 10-K document.
	7.	Serialization: Saves a JSON record per filing containing:
	•	ticker, cik, accession
	•	filing_date, form, document_url
	•	text (the extracted filing body)

### Output Structure
data/
└─ AAPL/
   ├─ 0000320193-21-000010.json
   ├─ 0000320193-20-000010.json
   └─ ...
└─ MSFT/
   ├─ 0000789019-20-000010.json
   └─ ...
### Customization & Best Practices
	•	User-Agent: SEC requires a descriptive User-Agent; set it to your app name and contact email.
	•	Rate Limiting: The script includes a short time.sleep(0.1) between downloads to respect SEC limits. Adjust if needed.
