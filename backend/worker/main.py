"""Worker entry point."""
import argparse
import asyncio
import logging
import signal
import sys

from worker.config import get_worker_settings
from worker.scheduler import WorkerScheduler


def setup_logging(level: str) -> None:
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def run_scheduler(scheduler: WorkerScheduler) -> None:
    """Run the scheduler until interrupted."""
    stop_event = asyncio.Event()
    
    def signal_handler():
        logging.info("Received shutdown signal")
        stop_event.set()
    
    # Handle signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    scheduler.start()
    
    # Wait for shutdown signal
    await stop_event.wait()
    
    # Cleanup
    await scheduler.shutdown()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="StreamRank Background Worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for cron jobs)",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate configuration and exit",
    )
    args = parser.parse_args()
    
    settings = get_worker_settings()
    setup_logging(settings.log_level)
    
    logger = logging.getLogger(__name__)
    
    # Validate config mode
    if args.validate_config:
        logger.info("Configuration validation:")
        logger.info(f"  Database URL: {settings.database_url[:30]}...")
        logger.info(f"  YouTube API Key: {'✓ Set' if settings.youtube_api_key else '✗ Missing'}")
        logger.info(f"  Poll Interval: {settings.poll_interval_minutes} minutes")
        logger.info(f"  Retention Days: {settings.retention_days}")
        
        if not settings.youtube_api_key:
            logger.error("YOUTUBE_API_KEY is required")
            sys.exit(1)
        
        logger.info("Configuration is valid")
        return
    
    scheduler = WorkerScheduler(settings)
    
    if args.once:
        # Run once mode
        logger.info("Running in single-execution mode")
        asyncio.run(scheduler.run_once())
    else:
        # Continuous mode
        logger.info("Starting continuous worker")
        asyncio.run(run_scheduler(scheduler))


if __name__ == "__main__":
    main()
