"""Aiogram Bot + Dispatcher factory.

Exposes :func:`build_bot` which constructs a configured Bot and a Dispatcher
with every router attached. The lifecycle owner (``main.py``) starts the
polling loop.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from ..config import Settings
from .handlers import register_all

log = logging.getLogger(__name__)


def build_bot(settings: Settings) -> tuple[Bot, Dispatcher]:
    if not settings.bot_token:
        raise RuntimeError(
            "BOT_TOKEN is not configured. Set it in the environment or .env file."
        )
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    register_all(dp)
    return bot, dp
