thonimport logging
from typing import List, Dict, Any
from urllib.parse import urlparse, parse_qs, urlunparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class ResultParser:
    """
    Parses search engine HTML and extracts LinkedIn company URLs.
    """

    @staticmethod
    def _normalize_linkedin_url(raw_url: str) -> str | None:
        """
        Normalizes a raw URL from a search result into a clean LinkedIn company URL.

        Handles redirect wrappers (e.g. /url?q=...) commonly used by search engines.
        """
        if not raw_url:
            return None

        # Handle redirect URLs like "/url?q=https://www.linkedin.com/company/google&..."
        parsed = urlparse(raw_url)

        if "linkedin.com" not in parsed.netloc and not raw_url.startswith("http"):
            # Might be a redirect path that contains the LinkedIn URL as a query param
            query = parse_qs(parsed.query)
            candidate_list = query.get("q") or query.get("url") or []
            if candidate_list:
                raw_url = candidate_list[0]
                parsed = urlparse(raw_url)

        if "linkedin.com" not in parsed.netloc:
            return None

        # Only keep company profiles
        if "/company/" not in parsed.path:
            return None

        # Strip tracking query params and fragments
        clean = parsed._replace(query="", fragment="")
        normalized = urlunparse(clean)

        # Normalize trailing slashes
        if normalized.endswith("/"):
            normalized = normalized.rstrip("/")

        return normalized

    @staticmethod
    def extract_linkedin_results(html: str, search_query: str) -> List[Dict[str, Any]]:
        """
        Extracts LinkedIn company search results from a search engine HTML page.

        Returns a list of dicts with keys: title, link, searchQuery.
        """
        soup = BeautifulSoup(html, "html.parser")
        results: List[Dict[str, Any]] = []

        # Strategy: scan all <a> tags; filter those that contain linkedin.com/company
        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            if not href:
                continue

            normalized = ResultParser._normalize_linkedin_url(href)
            if not normalized:
                continue

            title_text = anchor.get_text(strip=True) or search_query

            record = {
                "title": title_text,
                "link": normalized,
                "searchQuery": search_query,
            }
            results.append(record)

        logger.debug(
            "Parser extracted %d raw LinkedIn result(s) for search query '%s'",
            len(results),
            search_query,
        )

        return results