r"""
SEC EDGAR Filing Downloader for S&P 500 Companies

This script downloads 10-K, 10-Q, and Company Facts for S&P 500 companies
from the SEC EDGAR API. It's designed to run on a server and only download
missing documents.

Configuration:
    START_DATE: Initial date for data retrieval (e.g., "2023-01-01")
    MODE: "DEMO" (5 companies) or "FULL" (all S&P 500)

Produces:
    data/<TICKER>/<ACCESSION>.json      # for 10-K & 10-Q
    data/<TICKER>/<TICKER>_CF.json      # for Company Facts
"""

from dotenv import load_dotenv
load_dotenv()

#!/usr/bin/env python3
r"""
SEC EDGAR Filing Downloader for S&P 500 Companies

This script downloads 10-K, 10-Q, and Company Facts for S&P 500 companies
from the SEC EDGAR API. It's designed to run on a server and only download
missing documents.

Configuration:
    START_DATE: Initial date for data retrieval (e.g., "2023-01-01")
    MODE: "DEMO" (5 companies) or "FULL" (all S&P 500)

Produces:
    data/<TICKER>/<ACCESSION>.json      # for 10-K & 10-Q
    data/<TICKER>/<TICKER>_CF.json      # for Company Facts
"""

import os, json, time, logging, requests, re, html
from datetime import datetime, date
from dateutil.parser import parse as parse_date

# ─── CONFIGURATION ──────────────────────────────────────────────────────────────
START_DATE = os.getenv("START_DATE", "2023-01-01")
MODE = os.getenv("MODE", "DEMO")

# Your contact information for SEC User-Agent
USER_AGENT = os.getenv("USER_AGENT")

# ─── Constants ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = "data"
MAPPING_FILE = "company_tickers.json"
WANTED_FORMS = ["10-K", "10-Q", "CF"]
MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"

# Demo mode companies (top 5 S&P 500 by market cap)
DEMO_COMPANIES = ["AAPL"]

# optional HTML stripper
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


# ─── Get S&P 500 companies ──────────────────────────────────────────────────────
def get_sp500_tickers() -> list[str]:
    """Fetch current S&P 500 companies from Wikipedia"""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        
        # Try BeautifulSoup first for better parsing
        if BeautifulSoup:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Find the main S&P 500 table
            table = soup.find('table', {'id': 'constituents'})
            if not table:
                table = soup.find('table', class_='wikitable sortable')
            
            tickers = []
            if table:
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        # First cell should contain the ticker
                        ticker_text = cells[0].get_text(strip=True)
                        # Clean up ticker (remove any extra characters)
                        ticker = re.sub(r'[^A-Z.]', '', ticker_text.upper())
                        if ticker and len(ticker) <= 5:
                            tickers.append(ticker)
        else:
            # Fallback to regex approach with better patterns
            patterns = [
                r'<td[^>]*>([A-Z]{1,5}(?:\.[A-Z])?)</td>',
                r'>([A-Z]{2,5})</a></td>',
                r'<td[^>]*><a[^>]*>([A-Z]{1,5}(?:\.[A-Z])?)</a></td>'
            ]
            
            tickers = []
            for pattern in patterns:
                matches = re.findall(pattern, r.text)
                if matches:
                    tickers.extend(matches)
                    
            tickers = list(set(tickers))
            tickers = [t for t in tickers if len(t) <= 5 and re.match(r'^[A-Z]+(\.[A-Z])?$', t)]
        
        # Remove duplicates
        tickers = list(set(tickers))
        
        logging.info(f"Found {len(tickers)} S&P 500 tickers")
        return tickers[:500]  # Limit to 500 to be safe
    except Exception as e:
        logging.error(f"Failed to fetch S&P 500 list: {e}")
        # Fallback to a hardcoded list of major S&P 500 companies
        return [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK.B", "TSLA", 
            "JPM", "JNJ", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV", "PEP",
            "KO", "PFE", "WMT", "TMO", "CSCO", "ABT", "CRM", "NKE", "ACN",
            "LLY", "COST", "DIS", "ADBE", "VZ", "NEE", "CMCSA", "INTC", "DHR",
            "WFC", "TXN", "PM", "RTX", "SPGI", "UNP", "HON", "QCOM", "BMY",
            "UPS", "BA", "SBUX", "T", "MS", "LOW", "GS", "ELV", "CVS", "AXP"
        ]


# ─── Mapping ticker→CIK ─────────────────────────────────────────────────────────
def load_ticker_cik_mapping(mapping_file: str, user_agent: str) -> dict[str,str]:
    if not os.path.exists(mapping_file):
        logging.info(f"Downloading ticker→CIK mapping from {MAPPING_URL}")
        r = requests.get(MAPPING_URL, headers={"User-Agent": user_agent})
        r.raise_for_status()
        with open(mapping_file, "w") as f:
            f.write(r.text)
    data = json.load(open(mapping_file, encoding="utf-8"))
    entries = data.values() if isinstance(data, dict) else data
    return {e["ticker"].upper(): str(e["cik_str"]) for e in entries}


# ─── Fetch ALL company submissions including archived ones ──────────────────────
def fetch_all_company_filings(pad_cik: str, user_agent: str) -> tuple[list, list, list]:
    """
    Fetch all company filings, including those in additional archive files.
    Returns combined lists of (forms, dates, accessions)
    """
    url = f"https://data.sec.gov/submissions/CIK{pad_cik}.json"
    logging.info(f"Fetching submissions for CIK {pad_cik}")
    r = requests.get(url, headers={"User-Agent": user_agent})
    r.raise_for_status()
    subs = r.json()
    
    # Start with recent filings
    recent = subs.get("filings", {}).get("recent", {})
    all_forms = recent.get("form", [])
    all_dates = recent.get("filingDate", [])
    all_accessions = recent.get("accessionNumber", [])
    
    # Check for additional filing files (common for banks and large filers)
    files = subs.get("filings", {}).get("files", [])
    if files:
        logging.info(f"  Found {len(files)} additional filing files for CIK {pad_cik}")
        for file_ref in files:
            file_name = file_ref.get("name", "")
            if file_name:
                file_url = f"https://data.sec.gov/submissions/{file_name}"
                logging.info(f"  Fetching additional filings from {file_name}")
                try:
                    r = requests.get(file_url, headers={"User-Agent": user_agent})
                    r.raise_for_status()
                    additional_data = r.json()
                    
                    # Append the additional filings
                    all_forms.extend(additional_data.get("form", []))
                    all_dates.extend(additional_data.get("filingDate", []))
                    all_accessions.extend(additional_data.get("accessionNumber", []))
                    
                    time.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logging.error(f"  Failed to fetch additional filings from {file_name}: {e}")
    
    return all_forms, all_dates, all_accessions


# ─── Check if form matches our criteria ─────────────────────────────────────────
def is_matching_form(form: str, wanted_forms: list[str]) -> bool:
    """
    Check if a form type matches our wanted forms, including amended versions.
    E.g., both "10-K" and "10-K/A" match if "10-K" is wanted.
    """
    form_upper = form.upper()
    for wanted in wanted_forms:
        if wanted == "CF":
            continue
        # Match exact form or amended version (with /A suffix)
        if form_upper == wanted or form_upper.startswith(f"{wanted}/"):
            return True
    return False


# ─── Clean & extract 10-K/10-Q text ─────────────────────────────────────────────
def clean_filing_text(text: str) -> str:
    # decode unicode escapes
    text = text.encode("utf-8").decode("unicode_escape", errors="ignore")
    # fix mojibake
    try:
        text = text.encode("latin-1").decode("utf-8", errors="ignore")
    except Exception:
        pass
    # strip checkboxes
    text = re.sub(r"[\u2610\u2611\u2612]", "", text)
    # collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return html.unescape(text)


def extract_filing_text(raw: str, form_type: str) -> str:
    # Normalize form type for extraction (remove /A suffix)
    base_form = form_type.split("/")[0]
    
    fragments = []
    markers = [
        f"FORM {base_form}",
        "UNITED STATES SECURITIES AND EXCHANGE COMMISSION",
        "ANNUAL REPORT", "QUARTERLY REPORT"
    ]
    for doc in raw.split("<DOCUMENT>")[1:]:
        m = re.search(r"<TYPE>\s*([^\s<]+)", doc, flags=re.IGNORECASE)
        if not m:
            continue
        doc_type = m.group(1).upper()
        # Match document type flexibly
        if not (doc_type == form_type or doc_type == base_form):
            continue
            
        body = doc.split("<TEXT>", 1)[1] if "<TEXT>" in doc else doc
        # strip inline XBRL
        body = re.sub(r"<ix:[^>]+?>", "", body, flags=re.IGNORECASE)
        body = re.sub(r"</ix:[^>]+?>", "", body, flags=re.IGNORECASE)
        # strip HTML/XML
        if BeautifulSoup:
            text = BeautifulSoup(body, "html.parser").get_text(separator=" ")
        else:
            text = re.sub(r"<[^>]+>", " ", body)
        # normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        # trim to first marker
        lo = text.lower()
        for mk in markers:
            i = lo.find(mk.lower())
            if i != -1:
                text = text[i:]
                break
        # drop everything before the core Item 1.
        it = re.search(r"\bITEM\s+1[A-Z]?\.", text, flags=re.IGNORECASE)
        if it:
            text = text[it.start():]
        fragments.append(clean_filing_text(text))

    return "\n\n---\n\n".join(fragments)


# ─── Extract Company Facts → plain-English snippets ─────────────────────────────
def extract_facts_text(cf_json: dict, start: datetime.date, end: datetime.date) -> str:
    snippets = []
    entity = cf_json.get("entityName", "")
    usgaap  = cf_json.get("facts", {}).get("us-gaap", {})
    for concept, info in usgaap.items():
        for unit, items in info.get("units", {}).items():
            for item in items:
                date_str = item.get("end") or item.get("instant")
                val      = item.get("val")
                if val is None or date_str is None:
                    continue
                dt = parse_date(date_str).date()
                if (start and dt < start) or (end and dt > end):
                    continue
                # pretty-print
                lbl = concept.replace("StockholdersEquity", "Shareholders' Equity")
                snippets.append(
                    f"As of {date_str}, {lbl} for {entity} was {val} {unit}."
                )
    # join into one text blob
    return "\n\n".join(snippets)


# ─── Main function ──────────────────────────────────────────────────────────────
def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    
    # Parse configuration
    start_date = parse_date(START_DATE).date()
    end_date = date.today()
    
    logging.info(f"SEC EDGAR Filing Downloader")
    logging.info(f"Mode: {MODE}")
    logging.info(f"Date range: {start_date} to {end_date}")
    logging.info(f"User-Agent: {USER_AGENT}")
    
    # Get list of tickers based on mode
    if MODE == "DEMO":
        tickers = DEMO_COMPANIES
        logging.info(f"Demo mode: Processing {len(tickers)} companies: {', '.join(tickers)}")
    else:
        tickers = get_sp500_tickers()
        logging.info(f"Full mode: Processing {len(tickers)} S&P 500 companies")
    
    # Load ticker-CIK mapping
    mapping = load_ticker_cik_mapping(MAPPING_FILE, USER_AGENT)
    
    # Statistics
    stats = {
        "total_companies": len(tickers),
        "processed": 0,
        "skipped": 0,
        "downloads": 0,
        "errors": 0,
        "missing_tickers": []
    }
    
    # Process each ticker
    for ticker in tickers:
        ticker = ticker.upper()
        cik = mapping.get(ticker)
        
        if not cik:
            logging.warning(f"{ticker} not in mapping—skipping")
            stats["missing_tickers"].append(ticker)
            stats["skipped"] += 1
            continue
        
        logging.info(f"\nProcessing {ticker} (CIK: {cik})")
        stats["processed"] += 1
        
        try:
            pad = cik.zfill(10)
            # Fetch ALL filings including archived ones
            forms, dates, accs = fetch_all_company_filings(pad, USER_AGENT)
            
            outdir = os.path.join(OUTPUT_DIR, ticker)
            os.makedirs(outdir, exist_ok=True)
            
            # Count filings in date range
            filings_in_range = 0
            
            # ─── Process 10-K and 10-Q filings ─────────────────────────
            for form, ds, acc in zip(forms, dates, accs):
                if not is_matching_form(form, ["10-K", "10-Q"]):
                    continue
                
                fd = datetime.strptime(ds, "%Y-%m-%d").date()
                if fd < start_date or fd > end_date:
                    continue
                
                filings_in_range += 1
                
                acc_nd = acc.replace("-", "")
                url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nd}/{acc}.txt"
                dest = os.path.join(outdir, f"{acc}.json")
                
                if os.path.exists(dest):
                    logging.debug(f"  {form} {ds}: Already exists—skipping")
                    continue
                
                logging.info(f"  Downloading {form} filed on {ds}")
                try:
                    r = requests.get(url, headers={"User-Agent": USER_AGENT})
                    r.raise_for_status()
                    txt = extract_filing_text(r.text, form_type=form.upper())
                    rec = {
                        "ticker": ticker,
                        "cik": pad,
                        "accession": acc,
                        "filing_date": ds,
                        "form": form.upper(),
                        "url": url,
                        "text": txt
                    }
                    with open(dest, "w", encoding="utf-8") as o:
                        json.dump(rec, o, indent=2, ensure_ascii=False)
                    stats["downloads"] += 1
                    time.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logging.error(f"  Failed to download {form}: {e}")
                    stats["errors"] += 1
            
            logging.info(f"  Found {filings_in_range} 10-K/10-Q filings in date range")
            
            # ─── Process Company Facts ──────────────────────────────────
            accession = f"{ticker}_CF"
            cf_dest = os.path.join(outdir, f"{accession}.json")
            
            if os.path.exists(cf_dest):
                logging.debug(f"  Company Facts: Already exists—skipping")
            else:
                cf_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{pad}.json"
                logging.info(f"  Downloading Company Facts")
                try:
                    r = requests.get(cf_url, headers={"User-Agent": USER_AGENT})
                    r.raise_for_status()
                    cf_json = r.json()
                    text = extract_facts_text(cf_json, start_date, end_date)
                    rec = {
                        "ticker": ticker,
                        "cik": pad,
                        "accession": accession,
                        "filing_date": "",
                        "form": "CF",
                        "url": cf_url,
                        "text": text
                    }
                    with open(cf_dest, "w", encoding="utf-8") as o:
                        json.dump(rec, o, indent=2, ensure_ascii=False)
                    stats["downloads"] += 1
                    time.sleep(0.1)  # Rate limiting
                except Exception as e:
                    logging.error(f"  Failed to download Company Facts: {e}")
                    stats["errors"] += 1
                    
        except Exception as e:
            logging.error(f"Failed to process {ticker}: {e}")
            stats["errors"] += 1
    
    # ─── Final Summary ──────────────────────────────────────────────────────────
    logging.info("\n" + "="*60)
    logging.info("DOWNLOAD SUMMARY")
    logging.info("="*60)
    logging.info(f"Mode: {MODE}")
    logging.info(f"Date range: {start_date} to {end_date}")
    logging.info(f"Total companies: {stats['total_companies']}")
    logging.info(f"Successfully processed: {stats['processed']}")
    logging.info(f"Skipped (no CIK mapping): {stats['skipped']}")
    logging.info(f"New downloads: {stats['downloads']}")
    logging.info(f"Errors: {stats['errors']}")
    
    if stats["missing_tickers"]:
        logging.info(f"Missing tickers: {', '.join(stats['missing_tickers'][:10])}")
        if len(stats["missing_tickers"]) > 10:
            logging.info(f"  ... and {len(stats['missing_tickers']) - 10} more")
    
    if stats["errors"] == 0 and stats["skipped"] < stats["total_companies"] / 2:
        logging.info("\n✅ Download completed successfully!")
        return 0
    else:
        logging.error("\n❌ Download completed with errors or warnings!")
        return 1


if __name__ == "__main__":
    exit(main())