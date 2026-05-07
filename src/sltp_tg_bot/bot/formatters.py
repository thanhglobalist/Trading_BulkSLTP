"""Display formatters (status / position / header).

All output is MarkdownV2-safe — values are escaped via :func:`mdv2_escape`
before being interpolated into Markdown templates.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from .. import __version__
from ..i18n import t
from ..utils import format_money, format_pl, mdv2_escape, truncate


def render_header(
    *,
    alias: str,
    equity: Optional[float],
    pl: Optional[float],
    currency: str,
    lang: str,
    has_data: bool = True,
) -> str:
    """Header line shown at the top of every account-scoped screen."""
    a = mdv2_escape(alias)
    if not has_data or equity is None:
        return mdv2_escape(t("header_no_data", lang, alias=a, ver=__version__))
    return mdv2_escape(
        t(
            "header_fmt",
            lang,
            alias=a,
            equity=format_money(equity, currency),
            pl=format_pl(pl or 0.0, currency),
            ver=__version__,
        )
    )


def render_status(
    *,
    account: Mapping[str, Any],
    state: Mapping[str, Any],
    lang: str,
) -> str:
    """Render a /status reply.

    ``state`` is whatever the EA returned in the last heartbeat / status job
    (equity, balance, margin level, position count, etc.).
    """
    alias = mdv2_escape(account["alias"])
    title = t("status_title", lang, alias=alias)
    currency = account.get("base_currency") or "USD"
    equity = state.get("equity")
    balance = state.get("balance")
    pl = state.get("floating_pl")
    margin_level = state.get("margin_level")
    positions = state.get("positions_count")

    lines = [title, ""]
    if equity is not None:
        lines.append(f"• Equity: `{mdv2_escape(format_money(equity, currency))}`")
    if balance is not None:
        lines.append(f"• Balance: `{mdv2_escape(format_money(balance, currency))}`")
    if pl is not None:
        lines.append(f"• P/L: `{mdv2_escape(format_pl(pl, currency))}`")
    if margin_level is not None:
        lines.append(f"• Margin: `{mdv2_escape(f'{margin_level:.2f}%')}`")
    if positions is not None:
        lines.append(f"• Positions: `{positions}`")
    return "\n".join(lines)


def render_positions(
    *,
    account: Mapping[str, Any],
    positions: Iterable[Mapping[str, Any]],
    lang: str,
) -> str:
    alias = mdv2_escape(account["alias"])
    title = t("positions_title", lang, alias=alias)
    pos_list = list(positions)
    if not pos_list:
        return f"{title}\n\n{mdv2_escape(t('no_positions', lang))}"
    currency = account.get("base_currency") or "USD"
    lines = [title, ""]
    for p in pos_list:
        ticket = p.get("ticket", "?")
        symbol = p.get("symbol", "?")
        side = (p.get("side") or "").upper()
        volume = p.get("volume", "?")
        price = p.get("open_price", "?")
        pl = p.get("profit", 0.0)
        line = (
            f"`#{mdv2_escape(str(ticket))}` "
            f"{mdv2_escape(symbol)} {mdv2_escape(side)} "
            f"{mdv2_escape(str(volume))} @ {mdv2_escape(str(price))} → "
            f"`{mdv2_escape(format_pl(pl, currency))}`"
        )
        lines.append(truncate(line, 200))
    return "\n".join(lines)


def render_result(*, success: bool, summary: str, lang: str) -> str:
    if success:
        return mdv2_escape(t("result_ok", lang, summary=summary))
    return mdv2_escape(t("result_fail", lang, reason=summary))
