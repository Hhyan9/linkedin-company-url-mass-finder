thonfrom typing import Iterator

class PaginationHandler:
    """
    Encapsulates simple pagination logic for search engines.
    """

    @staticmethod
    def calculate_offset(page: int, per_page: int) -> int:
        """
        Calculate zero-based offset for a given 1-based page number.

        Example:
            page=1, per_page=10 -> offset 0
            page=2, per_page=10 -> offset 10
        """
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 1
        return (page - 1) * per_page

    @staticmethod
    def iter_pages(start_page: int, max_pages: int) -> Iterator[int]:
        """
        Yield page numbers starting from start_page up to start_page + max_pages - 1.
        Ensures page numbers are at least 1.
        """
        if start_page < 1:
            start_page = 1
        if max_pages < 1:
            max_pages = 1

        end_page = start_page + max_pages
        for page in range(start_page, end_page):
            yield page