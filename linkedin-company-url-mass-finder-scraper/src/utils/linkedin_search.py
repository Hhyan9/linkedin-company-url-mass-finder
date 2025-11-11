thonimport logging
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Iterable
from urllib.parse import urlencode

import requests

from .pagination_handler import PaginationHandler
from .result_parser import ResultParser

logger = logging.getLogger(__name__)

@dataclass
class SearchConfig:
    search_engine: str = "https://www.bing.com/search"
    query_template: str = "site:linkedin.com/company {company}"
    request_timeout_seconds: int = 10
    request_delay_seconds: float = 1.0
    user_agent: str = (
        "Mozilla/5.0 (compatible; LinkedInCompanyURLMassFinder/1.0)"
    )

class LinkedInCompanySearcher:
    """
    Performs web search queries to find LinkedIn company URLs for given names.

    This uses a generic search engine endpoint defined in settings, rather than
    scraping LinkedIn directly. It looks for linkedin.com/company links in
    the search results page.
    """

    def __init__(self, settings: Dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self.config = SearchConfig(
            search_engine=settings.get("search_engine", SearchConfig.search_engine),
            query_template=settings.get(
                "query_template",
                SearchConfig.query_template,
            ),
            request_timeout_seconds=int(
                settings.get(
                    "request_timeout_seconds",
                    SearchConfig.request_timeout_seconds,
                )
            ),
            request_delay_seconds=float(
                settings.get(
                    "request_delay_seconds",
                    SearchConfig.request_delay_seconds,
                )
            ),
            user_agent=settings.get("user_agent", SearchConfig.user_agent),
        )

        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": self.config.user_agent,
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def _build_search_url(
        self,
        company: str,
        page: int,
        results_per_page: int,
    ) -> str:
        offset = PaginationHandler.calculate_offset(page, results_per_page)
        query = self.config.query_template.format(company=company)

        # Bing-style parameters: "first" defines offset, "count" defines page size.
        params = {
            "q": query,
            "first": str(offset + 1),  # Bing is 1-based
            "count": str(results_per_page),
        }
        url = f"{self.config.search_engine}?{urlencode(params)}"
        logger.debug("Built search URL for '%s' (page=%d): %s", company, page, url)
        return url

    def _fetch_page(self, url: str) -> str:
        logger.debug("Fetching URL: %s", url)
        response = self._session.get(url, timeout=self.config.request_timeout_seconds)
        response.raise_for_status()
        return response.text

    def search_company(
        self,
        company: str,
        results_per_company: int,
        start_page: int,
        max_pages: int,
    ) -> List[Dict[str, Any]]:
        """
        Search for a single company's LinkedIn URLs.

        Returns a list of dictionaries with keys: title, link, searchQuery.
        """
        logger.info("Searching LinkedIn URLs for '%s'", company)
        all_results: List[Dict[str, Any]] = []
        seen_links: set[str] = set()

        for page in PaginationHandler.iter_pages(start_page, max_pages):
            url = self._build_search_url(
                company=company,
                page=page,
                results_per_page=results_per_company,
            )

            try:
                html = self._fetch_page(url)
            except requests.RequestException as exc:
                logger.warning(
                    "Request failed for '%s' (page %d): %s",
                    company,
                    page,
                    exc,
                )
                break

            page_results = ResultParser.extract_linkedin_results(
                html=html,
                search_query=company,
            )

            # De-duplicate by link
            new_items: List[Dict[str, Any]] = []
            for item in page_results:
                link = item.get("link")
                if not link:
                    continue
                if link in seen_links:
                    continue
                seen_links.add(link)
                new_items.append(item)

            logger.debug(
                "Page %d for '%s': found %d LinkedIn results (%d new after dedupe)",
                page,
                company,
                len(page_results),
                len(new_items),
            )

            all_results.extend(new_items)

            if len(all_results) >= results_per_company:
                logger.debug(
                    "Reached requested limit (%d) for '%s'",
                    results_per_company,
                    company,
                )
                break

            if not new_items:
                logger.debug(
                    "No new results found for '%s' on page %d; stopping.",
                    company,
                    page,
                )
                break

            # Be polite: brief delay between requests
            time.sleep(self.config.request_delay_seconds)

        limited_results = all_results[:results_per_company]
        logger.info(
            "Found %d LinkedIn URLs for '%s'",
            len(limited_results),
            company,
        )
        return limited_results

    def search_for_companies(
        self,
        companies: Iterable[str],
        results_per_company: int,
        start_page: int,
        max_pages: int,
    ) -> List[Dict[str, Any]]:
        """
        Search LinkedIn URLs for multiple companies.

        Returns a single list containing all result records.
        """
        combined_results: List[Dict[str, Any]] = []

        for company in companies:
            company = company.strip()
            if not company:
                continue

            logger.debug("Starting search for company: %s", company)
            try:
                company_results = self.search_company(
                    company=company,
                    results_per_company=results_per_company,
                    start_page=start_page,
                    max_pages=max_pages,
                )
                combined_results.extend(company_results)
            except Exception as exc:
                # Do not fail the whole run because of one company
                logger.exception(
                    "Unexpected error while searching for '%s': %s", company, exc
                )

        return combined_results