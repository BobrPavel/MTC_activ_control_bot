from aiogram import F, types, Router
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_get_cards,
    orm_get_card
)

from filters.chat_types import ChatTypeFilter

from kbds.reply import get_keyboard


PHONE_KB = get_keyboard(
    "Карты пробития",
    placeholder="Введите название техники",
    sizes=(1,),
)

user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


@user_private_router.message(F.text == "Карты пробития")
async def list_of_cards(callback: types.CallbackQuery, session: AsyncSession):
    cards = await orm_get_cards(session)
    text = ""
    for card in cards:
        text = text + f"{str(card.name)} \n"
    await callback.message.answer(f"Вот список техники. Если хотите посмотреть что-то подробнее, то напишите 'Карта_Название техники': \n\n{text}")



@user_private_router.message(F.text.startswith("Карта_"))
async def card_show(message: types.Message, session: AsyncSession):
    name = message.text.split("_")[-1]
    card = await orm_get_card(session, name)
    await message.answer_photo(card.image, card.name)