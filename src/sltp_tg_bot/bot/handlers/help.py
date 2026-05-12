from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="help")

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer("📘 Help:\n- /menu\n- /status\n- /positions\n- /lang")
