
"""
SEC EDGAR 10-K Downloader for RAG Projects

This script reads a CSV of tickers with date ranges and downloads 10-K filings
from the SEC EDGAR API. Filings are saved as JSON files suitable for RAG ingestion.
"""

import os
import csv
import json
import time
import argparse
import logging
import requests
import re
from datetime import datetime
from dateutil.parser import parse as parse_date

# Attempt to import BeautifulSoup for HTML cleaning
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# URL for ticker to CIK mapping
MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"

def load_ticker_cik_mapping(mapping_file, user_agent):
    if not os.path.exists(mapping_file):
        logging.info(f"Downloading ticker->CIK mapping from {MAPPING_URL}")
        resp = requests.get(MAPPING_URL, headers={"User-Agent": user_agent})
        resp.raise_for_status()
        with open(mapping_file, "w") as f:
            f.write(resp.text)
    with open(mapping_file) as f:
        data = json.load(f)
    entries = data.values() if isinstance(data, dict) else data
    mapping = {e["ticker"].upper(): str(e["cik_str"]) for e in entries}
    return mapping

def fetch_company_submissions(pad_cik, user_agent):
    url = f"https://data.sec.gov/submissions/CIK{pad_cik}.json"
    logging.info(f"Fetching company submissions for CIK {pad_cik}")
    resp = requests.get(url, headers={"User-Agent": user_agent})
    resp.raise_for_status()
    return resp.json()

def extract_filing_text(raw_text):
    """
    Clean raw filing text by:
      1. Extracting only the 10-K <TEXT> portion
      2. Removing XBRL tags
      3. Stripping HTML
      4. Chopping everything before the main header marker
      5. Collapsing whitespace
    Returns plain text suitable for RAG.
    """
    # 1) Split by <DOCUMENT> and find the 10-K section
    docs = raw_text.split("<DOCUMENT>")
    tenk = None
    for doc in docs:
        if "<TYPE>10-K" in doc:
            tenk = doc
            break
    if tenk and "<TEXT>" in tenk:
        tenk = tenk.split("<TEXT>", 1)[1]
    else:
        tenk = raw_text

    # 2) Remove inline XBRL tags
    cleaned = re.sub(r'<ix:[^>]+>', '', tenk)
    cleaned = re.sub(r'</ix:[^>]+>', '', cleaned)

    # 3) Remove HTML markup
    if BeautifulSoup:
        soup = BeautifulSoup(cleaned, 'html.parser')
        text = soup.get_text(separator='\n')
    else:
        text = re.sub(r'<[^>]+>', '', cleaned)

    # 4) Chop before header marker
    # Common marker: "UNITED STATES SECURITIES AND EXCHANGE COMMISSION"
    markers = [
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION",
        "FORM 10-K",
        "ANNUAL REPORT"
    ]
    lower = text.lower()
    start_idx = None
    for m in markers:
        pos = lower.find(m.lower())
        if pos != -1:
            start_idx = pos
            break
    if start_idx is not None:
        text = text[start_idx:]

    # 5) Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_csv(csv_file):
    rows = []
    with open(csv_file, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get("ticker", "").upper().strip()
            start = row.get("start_date", "").strip()
            end = row.get("end_date", "").strip()
            start_date = parse_date(start).date() if start else None
            end_date   = parse_date(end).date()   if end   else None
            rows.append({
                "ticker": ticker,
                "start_date": start_date,
                "end_date": end_date
            })
    return rows

def main():
    parser = argparse.ArgumentParser(description="Download 10-K filings from SEC EDGAR for RAG.")
    parser.add_argument("csv_file", help="CSV file with columns: ticker,start_date,end_date")
    parser.add_argument("--output-dir", default="data", help="Directory to save filings")
    parser.add_argument("--mapping-file", default="company_tickers.json", help="Ticker->CIK mapping JSON file")
    parser.add_argument("--user-agent", required=True, help="User-Agent header for SEC requests")
    parser.add_argument("--force", action="store_true", help="Re-download filings even if JSON exists")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    rows = parse_csv(args.csv_file)
    logging.info(f"Processing {len(rows)} tickers from {args.csv_file}")

    mapping = load_ticker_cik_mapping(args.mapping_file, args.user_agent)

    for entry in rows:
        ticker = entry["ticker"]
        start_date = entry["start_date"]
        end_date   = entry["end_date"]

        cik_str = mapping.get(ticker)
        if not cik_str:
            logging.warning(f"Ticker {ticker} not found in mapping, skipping.")
            continue

        pad_cik = cik_str.zfill(10)
        submissions = fetch_company_submissions(pad_cik, args.user_agent)

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        total_10k = sum(1 for f in forms if f == "10-K")
        logging.info(f"{ticker}: found {total_10k} total 10-K filings in index")

        output_dir = os.path.join(args.output_dir, ticker)
        os.makedirs(output_dir, exist_ok=True)

        for idx, (form, date_str, accession) in enumerate(zip(forms, dates, accessions)):
            if form != "10-K":
                continue

            filing_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if start_date and filing_date < start_date:
                continue
            if end_date   and filing_date > end_date:
                continue

            filename = f"{accession}.json"
            dest_path = os.path.join(output_dir, filename)

            if os.path.exists(dest_path) and not args.force:
                logging.info(f"{dest_path} already exists, skipping.")
                continue

            directory_cik = str(int(cik_str))
            acc_nodash = accession.replace("-", "")
            primary_doc = primary_docs[idx] if idx < len(primary_docs) else f"{acc_nodash}.txt"
            doc_url = f"https://www.sec.gov/Archives/edgar/data/{directory_cik}/{acc_nodash}/{primary_doc}"
            logging.info(f"Downloading {doc_url}")

            try:
                resp = requests.get(doc_url, headers={"User-Agent": args.user_agent})
                resp.raise_for_status()
                raw_text = resp.text
                text = extract_filing_text(raw_text)
                record = {
                    "ticker": ticker,
                    "cik": pad_cik,
                    "accession": accession,
                    "filing_date": date_str,
                    "form": form,
                    "document_url": doc_url,
                    "text": text
                }
                with open(dest_path, "w") as f:
                    json.dump(record, f, indent=2)
                logging.info(f"Saved filing to {dest_path}")
                time.sleep(0.1)
            except Exception as e:
                logging.error(f"Failed to download {doc_url}: {e}")

if __name__ == "__main__":
    main()
