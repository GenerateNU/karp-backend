import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from app.services.similarity_computation import similarity_computation_service

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_dir / "similarity_computation.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


async def main() -> int:
    """Run the batch similarity computation"""
    try:
        logger.info("=" * 80)
        logger.info(f"Starting batch event similarity computation script at {datetime.now()}")
        logger.info("=" * 80)

        result = await similarity_computation_service.compute_all_event_similarities()

        logger.info("=" * 80)
        logger.info(f"Batch job completed successfully at {datetime.now()}")
        logger.info(f"Results: {result}")
        logger.info("=" * 80)

        return 0
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"Batch job failed at {datetime.now()}: {e}", exc_info=True)
        logger.error("=" * 80)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
