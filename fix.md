Okay, Agent, regarding the Data Ingestion pipeline, particularly fetching the 10-K filings from EDGAR, here is a robust Python script pattern that you should adapt and integrate into the **Data Ingestion Agent** module. This script handles reading the `companies.csv`, mapping tickers to CIKs, fetching submissions, filtering for 10-Ks, and downloading their index HTML files, all while respecting SEC guidelines.

**Task for the Data Ingestion Agent: Implement SEC Filing Downloader**

**1. Adapt and Integrate the Following Python Script:**

   This script will be the core of fetching the initial set of filing index pages.

   ```python
   import csv
   import os
   import time
   import requests
   from ratelimit import limits, sleep_and_retry # Ensure 'ratelimit' is in requirements.txt

   # ========== CONFIG ==========
   # These should ideally be configurable via the project's main config (config.yaml or .env)
   # and passed to the Data Ingestion Agent, rather than hardcoded here.
   # For now, you can use these as defaults if direct config integration is complex.
   USER_AGENT = "AInalyst/1.0 (YourProjectContactInfo)" # Replace with project-specific info
   CSV_PATH   = "./companies.csv"      # Path from project config
   OUT_DIR    = "./data/raw_filing_indexes" # Directory to save index HTMLs
   # Ensure OUT_DIR is created, perhaps in the main application setup or by this agent.
   # os.makedirs(OUT_DIR, exist_ok=True) # Agent should ensure this directory exists

   HEADERS    = {"User-Agent": USER_AGENT}

   # SEC allows up to 10 requests/sec on EDGAR APIs
   @sleep_and_retry
   @limits(calls=10, period=1)
   def _get_sec_url(url: str, **kwargs) -> requests.Response:
       """Wrapper for GET requests to SEC, applying rate limits and headers."""
       print(f"Fetching URL: {url}") # Good for logging
       response = requests.get(url, headers=HEADERS, **kwargs)
       response.raise_for_status() # Raise an exception for HTTP error codes
       return response

   def get_cik_from_ticker(ticker: str) -> str:
       """Return zero-padded 10-digit CIK for a given stock ticker."""
       # This mapping file can be large; consider downloading it once and caching it locally
       # for the duration of the script's run or even longer if updated infrequently.
       resp = _get_sec_url("https://www.sec.gov/files/company_tickers.json")
       data = resp.json()
       for company_info in data.values(): # The structure is a dict with integer keys
           if company_info.get("ticker", "").upper() == ticker.upper():
               return str(company_info["cik_str"]).zfill(10)
       raise KeyError(f"Ticker {ticker} not found in SEC mapping. SEC mapping structure might have changed.")

   def fetch_company_submissions(cik: str) -> dict:
       """Return the submissions JSON for this CIK (includes ALL filing types)."""
       url = f"https://data.sec.gov/submissions/CIK{cik}.json"
       return _get_sec_url(url).json()

   def find_10k_filing_indices(submissions_data: dict, start_year: int, end_year: int) -> list[dict]:
       """
       Scan the 'recent' filings for all 10-Ks in the given year range.
       Returns list of { 'filing_date', 'report_date', 'accession_number', 'primary_document', 'index_url' } entries.
       """
       if "filings" not in submissions_data or "recent" not in submissions_data["filings"]:
           print(f"Warning: 'filings' or 'recent' key not found in submissions data for CIK {submissions_data.get('cik')}. Skipping.")
           return []

       filings_recent = submissions_data["filings"]["recent"]
       # Ensure all expected keys are present to avoid KeyErrors
       required_keys = ["form", "filingDate", "reportDate", "accessionNumber", "primaryDocument"]
       for key in required_keys:
           if key not in filings_recent:
               print(f"Warning: Expected key '{key}' not found in 'recent' filings. Skipping CIK {submissions_data.get('cik')}.")
               return []

       forms = filings_recent["form"]
       filing_dates = filings_recent["filingDate"]
       report_dates = filings_recent["reportDate"] # Date the report is for
       accession_numbers = filings_recent["accessionNumber"]
       primary_documents = filings_recent["primaryDocument"] # e.g., 'd123456d10k.htm'

       cik_int_str = submissions_data["cik"] # CIK is already a string here
       matches = []

       for i in range(len(forms)):
           form = forms[i]
           filing_date_str = filing_dates[i]
           report_date_str = report_dates[i]
           accession_no = accession_numbers[i]
           primary_doc_name = primary_documents[i]

           try:
               filing_year = int(filing_date_str[:4])
           except ValueError:
               print(f"Warning: Could not parse year from filingDate '{filing_date_str}'. Skipping.")
               continue

           if form == "10-K" and start_year <= filing_year <= end_year:
               acc_nodash = accession_no.replace("-", "")
               # URL to the directory containing all filing documents
               # The primary_doc_name is relative to this directory
               # The index URL is constructed for the filing's landing page
               index_url = (
                   f"https://www.sec.gov/Archives/edgar/data/"
                   f"{cik_int_str}/{acc_nodash}/{accession_no}-index.html"
               )
               # URL to the primary 10-K document itself
               primary_doc_url = (
                   f"https://www.sec.gov/Archives/edgar/data/"
                   f"{cik_int_str}/{acc_nodash}/{primary_doc_name}"
               )

               matches.append({
                   "filing_date": filing_date_str,
                   "report_date": report_date_str,
                   "accession_number": accession_no,
                   "primary_document_name": primary_doc_name,
                   "primary_document_url": primary_doc_url, # URL to the actual 10-K
                   "index_url": index_url # URL to the index page
               })
       return matches

   def download_filing_document(filing_info: dict, ticker: str, output_directory: str) -> str:
       """Downloads the primary filing document (HTML/text) and writes to disk."""
       # We want the primary document URL, not the index URL for the final content
       document_url = filing_info["primary_document_url"]
       try:
           content = _get_sec_url(document_url).text
           # Use accession number for uniqueness, and include filing date for clarity
           # Ensure filename is OS-compatible
           safe_primary_doc_name = filing_info["primary_document_name"].replace("/", "_")
           fname = f"{ticker}_{filing_info['filing_date']}_{filing_info['accession_number']}_{safe_primary_doc_name}"
           # Ensure filename doesn't get too long or have problematic characters
           fname = "".join(c if c.isalnum() or c in ['_', '-','.'] else '_' for c in fname)

           path  = os.path.join(output_directory, fname)
           os.makedirs(output_directory, exist_ok=True) # Ensure dir exists

           with open(path, "w", encoding="utf-8") as f:
               f.write(content)
           print(f"   • Saved {filing_info['filing_date']} ({filing_info['accession_number']}) → {path}")
           return path
       except requests.exceptions.RequestException as e:
           print(f"   • Error downloading {document_url}: {e}")
           return "" # Return empty string or raise exception
       except IOError as e:
           print(f"   • Error saving file for {document_url}: {e}")
           return ""

   # This function would be called by the main Data Ingestion Agent logic
   def process_company_filings_from_csv(csv_filepath: str, output_dir: str, config_user_agent: str):
       global USER_AGENT # Allow modification of global if passed
       USER_AGENT = config_user_agent
       global HEADERS
       HEADERS = {"User-Agent": USER_AGENT}

       if not os.path.exists(csv_filepath):
           print(f"Error: CSV file not found at {csv_filepath}")
           return

       processed_files_summary = {}

       with open(csv_filepath, newline="", encoding="utf-8") as csvfile:
           reader = csv.DictReader(csvfile) # Use DictReader for easier column access
           for row in reader:
               try:
                   ticker = row["ticker"].strip()
                   company_name = row.get("company_name", ticker).strip() # Optional company_name
                   start_year = int(row["start_year"].strip())
                   end_year = int(row["end_year"].strip())
               except KeyError as e:
                   print(f"Skipping row due to missing key: {e}. Row: {row}")
                   continue
               except ValueError as e:
                   print(f"Skipping row due to invalid year format: {e}. Row: {row}")
                   continue

               print(f"\n→ Processing {ticker} ({company_name}) for filings from {start_year}–{end_year}")
               processed_files_summary[ticker] = []
               try:
                   cik = get_cik_from_ticker(ticker)
                   submissions = fetch_company_submissions(cik)
                   # We now directly get info for the primary 10-K document
                   target_filings_info = find_10k_filing_indices(submissions, start_year, end_year)

                   if not target_filings_info:
                       print(f"   • No 10-K filings found in the specified range for {ticker}.")
                       continue

                   company_specific_out_dir = os.path.join(output_dir, ticker) # Store filings in per-ticker subdirectories
                   os.makedirs(company_specific_out_dir, exist_ok=True)

                   for filing_detail in target_filings_info:
                       # Pass company_specific_out_dir to download_filing_document
                       saved_path = download_filing_document(filing_detail, ticker, company_specific_out_dir)
                       if saved_path:
                           processed_files_summary[ticker].append(saved_path)
                       time.sleep(0.1) # Additional courtesy pause

               except KeyError as e: # Specifically for ticker not found
                   print(f"   • Could not process {ticker}: {e}")
               except requests.exceptions.RequestException as e:
                   print(f"   • Network or API error for {ticker}: {e}")
               except Exception as e:
                   print(f"   • An unexpected error occurred for {ticker}: {e}")
       
       print("\n========== SUMMARY ==========")
       for ticker, files in processed_files_summary.items():
           print(f"{ticker}: Downloaded {len(files)} filings.")
           # for f_path in files:
           #     print(f"  - {f_path}")


   # Example of how the Data Ingestion Agent might call this:
   # if __name__ == "__main__":
   #     # This part would be integrated into your agent's workflow
   #     # Configuration values would come from your project's central config
   #     conf_csv_path = "./companies.csv" # From project config
   #     conf_output_dir = "./data/10k_filings_full" # Directory to save full 10-K documents
   #     conf_user_agent = "AInalyst/1.0 (contact@example.com)" # From project config
   #     process_company_filings_from_csv(conf_csv_path, conf_output_dir, conf_user_agent)