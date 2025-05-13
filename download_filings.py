#!/usr/bin/env python3
r"""
SEC EDGAR 10-K/10-Q Downloader for RAG Projects

Usage:
    python download_filings.py tickers.csv --user-agent "Name email"

Produces:
    data/<TICKER>/<ACCESSION>.json
"""

import os
import csv
import json
import time
import argparse
import logging
import requests
import re
import html
from datetime import datetime
from dateutil.parser import parse as parse_date

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

WANTED_FORMS = ["10-K", "10-Q"]
MAPPING_URL   = "https://www.sec.gov/files/company_tickers.json"

def load_ticker_cik_mapping(mapping_file: str, user_agent: str) -> dict[str,str]:
    if not os.path.exists(mapping_file):
        logging.info(f"Downloading ticker→CIK mapping from {MAPPING_URL}")
        r = requests.get(MAPPING_URL, headers={"User-Agent": user_agent})
        r.raise_for_status()
        with open(mapping_file, "w") as f:
            f.write(r.text)
    data = json.load(open(mapping_file))
    entries = data.values() if isinstance(data, dict) else data
    return {e["ticker"].upper(): str(e["cik_str"]) for e in entries}

def fetch_company_submissions(pad_cik: str, user_agent: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{pad_cik}.json"
    logging.info(f"Fetching submissions for CIK {pad_cik}")
    r = requests.get(url, headers={"User-Agent": user_agent})
    r.raise_for_status()
    return r.json()

def clean_filing_text(text: str) -> str:
    r"""
    1. Decode *all* \uXXXX escapes → real Unicode
    2. Fix mojibake (latin-1→utf-8)
    3. Remove checkbox symbols
    4. Strip boilerplate (checkbox paragraphs, rule definitions)
    5. Collapse whitespace
    6. Unescape HTML entities
    """
    # decode *any* \uXXXX
    text = text.encode("utf-8").decode("unicode_escape", errors="ignore")
    # fix mojibake
    try:
        text = text.encode("latin-1").decode("utf-8", errors="ignore")
    except Exception:
        pass
    # remove checkboxes
    text = re.sub(r"[\u2610\u2611\u2612]", "", text)
    # boilerplate
    for pat in [
        r"Indicate by check mark.*?Exchange Act\.",
        r"See the definitions of .*? in Rule .*?\."
    ]:
        text = re.sub(pat, "", text, flags=re.IGNORECASE|re.DOTALL)
    # whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return html.unescape(text)

def extract_filing_text(raw: str, form_type: str) -> str:
    fragments = []
    # markers to trim front
    markers = [
        f"FORM {form_type}",
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION",
        "ANNUAL REPORT", "QUARTERLY REPORT"
    ]
    for doc in raw.split("<DOCUMENT>")[1:]:
        m = re.search(r"<TYPE>\s*([^\s<]+)", doc, flags=re.IGNORECASE)
        if not m or m.group(1).upper() != form_type:
            continue
        body = doc.split("<TEXT>",1)[1] if "<TEXT>" in doc else doc
        # strip inline XBRL
        body = re.sub(r"<ix:[^>]+?>", "", body, flags=re.IGNORECASE)
        body = re.sub(r"</ix:[^>]+?>", "", body, flags=re.IGNORECASE)
        # strip HTML/XML
        if BeautifulSoup:
            text = BeautifulSoup(body, "html.parser").get_text(separator=" ")
        else:
            text = re.sub(r"<[^>]+>", " ", body)
        text = re.sub(r"\s+", " ", text).strip()
        # trim to first marker
        lo = text.lower()
        for mk in markers:
            i = lo.find(mk.lower())
            if i != -1:
                text = text[i:]
                break
        # drop before Item 1.
        it = re.search(r"\bITEM\s+1[A-Z]?\.", text, flags=re.IGNORECASE)
        if it:
            text = text[it.start():]
        fragments.append(clean_filing_text(text))
    return "\n\n---\n\n".join(fragments)

def parse_csv(csv_file: str) -> list[dict]:
    rows = []
    with open(csv_file, newline="") as f:
        rd = csv.reader(f)
        next(rd, None)
        for row in rd:
            if not row or row[0].startswith("#"): continue
            ticker = row[0].upper().strip()
            sd = parse_date(row[1]).date() if row[1].strip() else None
            ed = parse_date(row[2]).date() if row[2].strip() else None
            ff = row[3].strip().upper()
            if not ff or ff=="ALL":
                forms = WANTED_FORMS.copy()
            else:
                parts = re.split(r"[;,]", ff)
                forms = [p for p in parts if p in WANTED_FORMS]
            rows.append({
                "ticker": ticker,
                "start_date": sd,
                "end_date": ed,
                "forms": forms
            })
    return rows

def main():
    p = argparse.ArgumentParser(description="Download SEC 10-K/10-Q filings")
    p.add_argument("csv_file", help="CSV: ticker,start_date,end_date,forms")
    p.add_argument("--output-dir",   default="data",                 help="Where to save")
    p.add_argument("--mapping-file", default="company_tickers.json", help="Ticker→CIK JSON")
    p.add_argument("--user-agent",   required=True,                  help="SEC User-Agent")
    p.add_argument("--force",        action="store_true",             help="Overwrite existing")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    tasks   = parse_csv(args.csv_file)
    mapping = load_ticker_cik_mapping(args.mapping_file, args.user_agent)

    for t in tasks:
        ticker, start, end, want = t["ticker"], t["start_date"], t["end_date"], set(t["forms"])
        cik = mapping.get(ticker)
        if not cik:
            logging.warning(f"{ticker} not in mapping—skipping")
            continue

        pad = cik.zfill(10)
        subs = fetch_company_submissions(pad, args.user_agent)
        recent = subs.get("filings",{}).get("recent",{})
        forms  = recent.get("form",[])
        dates  = recent.get("filingDate",[])
        accs   = recent.get("accessionNumber",[])

        outdir = os.path.join(args.output_dir, ticker)
        os.makedirs(outdir, exist_ok=True)

        for form, ds, acc in zip(forms, dates, accs):
            fm = form.upper()
            if fm not in want: continue
            fd = datetime.strptime(ds, "%Y-%m-%d").date()
            if (start and fd<start) or (end and fd> end): continue

            acc_nd = acc.replace("-","")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nd}/{acc}.txt"
            dest= os.path.join(outdir, f"{acc}.json")
            if os.path.exists(dest) and not args.force:
                logging.info(f"{dest} exists—skipping")
                continue

            logging.info(f"Downloading {ticker} {fm} @ {ds}")
            try:
                r = requests.get(url, headers={"User-Agent": args.user_agent})
                r.raise_for_status()
                txt = extract_filing_text(r.text, form_type=fm)
                rec = {
                    "ticker":      ticker,
                    "cik":         pad,
                    "accession":   acc,
                    "filing_date": ds,
                    "form":        fm,
                    "url":         url,
                    "text":        txt
                }
                # write real Unicode (no \u escapes)
                with open(dest, "w", encoding="utf-8") as o:
                    json.dump(rec, o, indent=2, ensure_ascii=False)
                time.sleep(0.1)
            except Exception as e:
                logging.error(f"Failed {ticker} {fm}@{ds}: {e}")

if __name__ == "__main__":
    main()
