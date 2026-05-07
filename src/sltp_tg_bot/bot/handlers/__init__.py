"""Aiogram handler modules. Routers are aggregated by :func:`register_all`."""

from aiogram import Dispatcher

from . import admin, common, help as help_mod, menu, status, trading


def register_all(dp: Dispatcher) -> None:
    """Attach every handler router to the dispatcher (order matters)."""
    dp.include_router(common.router)
    dp.include_router(menu.router)
    dp.include_router(status.router)
    dp.include_router(trading.router)
    dp.include_router(admin.router)
    dp.include_router(help_mod.router)
