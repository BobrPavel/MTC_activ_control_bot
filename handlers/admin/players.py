from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from database.orm_query import (
    orm_get_players,
    orm_get_player,
    orm_delete_player,
    orm_change_status_player,
)
from kbds.inline import get_callback_btns
from states.admin_states import AddUser

from filters.chat_types import ChatTypeFilter, IsAdmin

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


@admin_router.message(F.text == "Игроки")
async def admin_players(message: types.Message):
    await message.answer(
        "Для подробного просмотра игрока введите player_Позывной",
        reply_markup=get_callback_btns(
            btns={"Новый игрок": "add-new-player", "Список игроков": "players-list"},
            sizes=(2,),
        ),
    )


@admin_router.callback_query(F.data == "players-list")
async def list_of_players(callback: types.CallbackQuery, session: AsyncSession):
    players = await orm_get_players(session)
    if not players:
        await callback.message.answer("Список игроков пуст.")
        return
    text = "\n".join(player.name for player in players)
    await callback.message.answer(f"Вот список игроков:\n\n{text}")


@admin_router.message(F.text.startswith("player_"))
async def show_player_info(message: types.Message, session: AsyncSession):
    player_name = message.text.removeprefix("player_")
    player = await orm_get_player(session, player_name)
    if not player:
        await message.answer(f"Игрок с позывным '{player_name}' не найден.")
        return
    text = f"{player.name} | {player.count} | {player.direction.name} | {player.statuses.name}."
    keyboard = get_callback_btns(
        btns={
            "🔄 позывной": f"change-player_{player.name}",
            "🔄 статус": f"change-status_{player.name}",
            "❌ Удалить": f"delete-player_{player.name}",
        },
        sizes=(2, 1),
    )
    await message.answer(text, reply_markup=keyboard)


@admin_router.callback_query(F.data == "add-new-player")
async def add_new_player(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AddUser.name)
    await callback.message.answer(
        "Введите позывной", reply_markup=types.ReplyKeyboardRemove()
    )


@admin_router.callback_query(F.data.startswith("change-player_"))
async def change_player_name(
    callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    player_name = callback.data.removeprefix("change-player_")
    player = await orm_get_player(session, player_name)
    if not player:
        await callback.message.answer(f"Игрок '{player_name}' не найден.")
        return

    await state.update_data(item_for_change=player, original_key=player_name)

    await state.set_state(AddUser.name)
    await callback.message.answer(
        "Введите новый позывной", reply_markup=types.ReplyKeyboardRemove()
    )


@admin_router.callback_query(F.data.startswith("change-status_"))
async def change_player_status(callback: types.CallbackQuery, session: AsyncSession):
    player_name = callback.data.removeprefix("change-status_")
    player = await orm_get_player(session, player_name)
    if not player:
        await callback.message.answer(f"Игрок '{player_name}' не найден.")
        return
    new_status = 2 if player.statuses_id == 1 else 1
    await orm_change_status_player(session, player_name, new_status)
    await callback.answer("Статус обновлён")


@admin_router.callback_query(F.data.startswith("delete-player_"))
async def delete_player(callback: types.CallbackQuery, session: AsyncSession):
    player_name = callback.data.removeprefix("delete-player_")
    success = await orm_delete_player(session, player_name)
    await callback.message.answer(
        f"Игрок '{player_name}' {'удалён.' if success else 'не найден или не удалён.'}"
    )
