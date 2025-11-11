thonimport json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def _ensure_parent_dir(path: Path) -> None:
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

def export_to_json(results: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Write scraped LinkedIn company results to a JSON file.

    Each item in `results` should contain: title, link, searchQuery.
    """
    _ensure_parent_dir(output_path)

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.error("Failed to write JSON to %s: %s", output_path, exc)
        raise

    logger.info(
        "Exported %d record(s) to %s",
        len(results),
        output_path,
    )