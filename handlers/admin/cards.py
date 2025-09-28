from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_get_cards,
    orm_get_card,
    orm_delete_card,
)
from kbds.inline import get_callback_btns
from states.admin_states import AddCard

from filters.chat_types import ChatTypeFilter, IsAdmin

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

@admin_router.message(F.text == "Карточки")
async def admin_cards(message: types.Message):
    await message.answer(
        "Для подробного просмотра карточки введите card_Название карточки",
        reply_markup=get_callback_btns(
            btns={"Новая карточка": "add-new-card", "Список карточек": "card-list"},
            sizes=(2,),
        ),
    )


@admin_router.callback_query(F.data == "card-list")
async def list_of_cards(callback: types.CallbackQuery, session: AsyncSession):
    cards = await orm_get_cards(session)
    if not cards:
        await callback.message.answer("Список карточек пуст.")
        return
    text = "\n".join(card.name for card in cards)
    await callback.message.answer(f"Вот список карточек:\n\n{text}")


@admin_router.message(F.text.startswith("card_"))
async def card_show(message: types.Message, session: AsyncSession):
    name = message.text.removeprefix("card_")
    card = await orm_get_card(session, name)
    if not card:
        await message.answer(f"Карточка с именем '{name}' не найдена.")
        return
    keyboard = get_callback_btns(
        btns={
            "Редактировать": f"change-card_{card.name}",
            "Удалить": f"delete_{card.name}",
        },
        sizes=(2,),
    )
    await message.answer_photo(
        photo=card.image, caption=card.name, reply_markup=keyboard
    )


@admin_router.callback_query(F.data == "add-new-card")
async def add_card(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AddCard.name)
    await callback.message.answer(
        "Введите название техники", reply_markup=types.ReplyKeyboardRemove()
    )


@admin_router.callback_query(F.data.startswith("delete_"))
async def delete_card(callback: types.CallbackQuery, session: AsyncSession):
    name = callback.data.removeprefix("delete_")
    success = await orm_delete_card(session, name)
    await callback.message.answer(
        f"Карточка '{name}' {'удалена.' if success else 'не найдена или не удалена.'}"
    )


@admin_router.callback_query(F.data.startswith("change-card_"))
async def start_edit_card(
    callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    name = callback.data.split("_")[-1]
    card = await orm_get_card(session, name)
    await state.update_data(item_for_change=card, original_key=name)
    await callback.message.answer("Введите новое название карточки:")
    await state.set_state(AddCard.name)
