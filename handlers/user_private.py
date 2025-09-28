from aiogram import F, types, Router
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_get_cards,
    orm_get_card
)

from filters.chat_types import ChatTypeFilter

from kbds.reply import get_keyboard


user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


# Показывает список карт
@user_private_router.message(CommandStart())
@user_private_router.message(F.text == "Карты пробития")
async def list_of_cards(message: types.Message, session: AsyncSession):
    cards = await orm_get_cards(session)
    if not cards:
        await message.answer("Список карт пуст.")
        return

    text = "\n".join(card.name for card in cards)
    await message.answer(
        f"Вот список техники. Если хотите посмотреть что-то подробнее, "
        f"напишите 'Карта_Название техники':\n\n{text}"
    )

# Показывает конкретную карту
@user_private_router.message(F.text.startswith("Карта_"))
async def card_show(message: types.Message, session: AsyncSession):
    name = message.text.removeprefix("Карта_").strip()
    card = await orm_get_card(session, name)

    if card:
        await message.answer_photo(card.image, caption=card.name)
    else:
        await message.answer("Карта с таким названием не найдена.")