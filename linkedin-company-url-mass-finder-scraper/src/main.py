thonimport argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure local src/ directory is on sys.path so we can import utils/*
CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.linkedin_search import LinkedInCompanySearcher  # noqa: E402
from output.exporter import export_to_json  # noqa: E402

def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

def load_settings(settings_path: Path) -> Dict[str, Any]:
    if not settings_path.is_file():
        logging.warning("Settings file not found at %s, using defaults.", settings_path)
        return {}

    try:
        with settings_path.open("r", encoding="utf-8") as f:
            settings = json.load(f)
            logging.debug("Loaded settings: %s", settings)
            return settings
    except Exception as exc:
        logging.error("Failed to read settings from %s: %s", settings_path, exc)
        return {}

def read_company_names(input_path: Path) -> List[str]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    companies: List[str] = []
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            name = line.strip()
            if name:
                companies.append(name)

    if not companies:
        raise ValueError(f"No company names found in {input_path}")

    logging.info("Loaded %d company names from %s", len(companies), input_path)
    return companies

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LinkedIn Company URL - Mass Finder"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(
            CURRENT_FILE.parent.parent / "data" / "sample_input.txt"
        ),
        help="Path to input text file containing company names (one per line).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(
            CURRENT_FILE.parent.parent / "data" / "sample_output.json"
        ),
        help="Path to JSON file where results will be written.",
    )
    parser.add_argument(
        "--settings",
        "-s",
        type=str,
        default=str(SRC_DIR / "config" / "settings.json"),
        help="Path to JSON settings file.",
    )
    parser.add_argument(
        "--results-per-company",
        "-r",
        type=int,
        default=None,
        help="Maximum number of LinkedIn URLs to return per company. "
             "If not provided, the value from settings.json is used.",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=None,
        help="Search start page (1-based). Overrides settings.json if provided.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to scan for each company. "
             "Overrides settings.json if provided.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging output.",
    )
    return parser.parse_args()

def main() -> None:
    args = parse_args()
    setup_logging(verbose=args.verbose)

    settings_path = Path(args.settings)
    settings = load_settings(settings_path)

    input_path = Path(args.input)
    output_path = Path(args.output)

    try:
        companies = read_company_names(input_path)
    except Exception as exc:
        logging.error("Could not read input companies: %s", exc)
        sys.exit(1)

    results_per_company = (
        args.results_per_company
        if args.results_per_company is not None
        else int(settings.get("results_per_company", 5))
    )
    start_page = (
        args.start_page
        if args.start_page is not None
        else int(settings.get("start_page", 1))
    )
    max_pages = (
        args.max_pages
        if args.max_pages is not None
        else int(settings.get("max_pages", 1))
    )

    logging.info(
        "Starting LinkedIn company URL search for %d companies "
        "(results_per_company=%d, start_page=%d, max_pages=%d)",
        len(companies),
        results_per_company,
        start_page,
        max_pages,
    )

    try:
        searcher = LinkedInCompanySearcher(settings=settings)
        results: List[Dict[str, Any]] = searcher.search_for_companies(
            companies=companies,
            results_per_company=results_per_company,
            start_page=start_page,
            max_pages=max_pages,
        )
    except Exception as exc:
        logging.exception("Search failed: %s", exc)
        sys.exit(1)

    try:
        export_to_json(results, output_path)
    except Exception as exc:
        logging.exception("Failed to export results: %s", exc)
        sys.exit(1)

    logging.info(
        "Finished. %d LinkedIn records written to %s",
        len(results),
        output_path,
    )

if __name__ == "__main__":
    main()