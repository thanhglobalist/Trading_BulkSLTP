"""Entry point — starts the Telegram bot and the FastAPI bridge in one process.

Run with::

    python -m sltp_tg_bot.main

or via the systemd unit shipped under ``systemd/``.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import asyncio
import logging
import signal
from typing import Optional

import uvicorn

from . import __version__, db
from .bot.app import build_bot
from .bridge.alerts import alerts_worker, jobs_expirer
from .bridge.api import build_app
from .config import get_settings


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )


async def _run_bot(bot, dp) -> None:
    """Run aiogram polling. Drops any pending updates on cold-start."""
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def _run_bridge(host: str, port: int) -> None:
    config = uvicorn.Config(
        app=build_app(),
        host=host,
        port=port,
        log_level="info",
        access_log=False,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main_async() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = logging.getLogger("sltp-tg-bot")
    log.info("starting sltp-tg-bot v%s", __version__)

    # Make sure the DB schema exists before anything boots.
    await db.init_schema(settings.db_path)

    bot, dp = build_bot(settings)

    tasks = [
        asyncio.create_task(_run_bot(bot, dp), name="bot"),
        asyncio.create_task(_run_bridge(settings.listen_host, settings.listen_port),
                            name="bridge"),
        asyncio.create_task(alerts_worker(bot), name="alerts"),
        asyncio.create_task(jobs_expirer(), name="expirer"),
    ]

    stop_event = asyncio.Event()

    def _stop(*_):
        log.info("shutdown signal received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:  # pragma: no cover — Windows
            pass

    done, pending = await asyncio.wait(
        tasks + [asyncio.create_task(stop_event.wait(), name="stop")],
        return_when=asyncio.FIRST_COMPLETED,
    )

    log.info("stopping background tasks")
    for task in pending:
        task.cancel()
    for task in pending:
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    try:
        await bot.session.close()
    except Exception:
        pass


def main() -> None:
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
