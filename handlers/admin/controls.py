from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.fsm.state import State, StatesGroup

from database.orm_query import (
    orm_get_players2,
    orm_update_player_plus,
    orm_update_player_minus,
)
from kbds.inline import get_callback_btns
from kbds.reply import get_keyboard

from filters.chat_types import ChatTypeFilter, IsAdmin

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

ADMIN_KB = get_keyboard("Карточки", "Игроки", "Отчёты", "Контроль", sizes=(2, 2))


class ActivControlFSM(StatesGroup):
    name = State()
    id = State()


# ✅ Старт команды "Контроль"
@admin_router.message(F.text == "Контроль")
async def start_control(
    message: types.Message, state: FSMContext, session: AsyncSession
):
    players = await orm_get_players2(session)
    await state.update_data(all_players=players, selected=[], result=[])

    await message.answer(
        "Введите позывной активного игрока", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(ActivControlFSM.name)


# ✅ Отмена
@admin_router.message(ActivControlFSM.name, F.data == "cancel_activ")
@admin_router.message(ActivControlFSM.id, F.data == "cancel_activ")
async def cancel_control(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


# ✅ Добавление игрока
@admin_router.message(ActivControlFSM.name, F.text)
async def add_player(message: types.Message, state: FSMContext):
    data = await state.get_data()
    player = message.text

    if player in data["all_players"]:
        selected = data.get("selected", [])
        if player not in selected:
            selected.append(player)
            await state.update_data(selected=selected)

        await message.answer(
            "Игрок добавлен. Введите ещё или нажмите кнопку.",
            reply_markup=get_callback_btns(
                btns={"Завершить": "+", "Отменить всё": "cancel_activ"}, sizes=(2,)
            ),
        )
    else:
        await message.answer("Такого игрока нет в базе. Возможно он в отпуске или его нужно выгнать")


# ✅ Показать список и предложить удалить
@admin_router.callback_query(F.data == "+")
async def show_selected(
    callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("selected", [])
    all_players = data.get("all_players", [])

    # Вычисляем result
    result = [p for p in all_players if p not in selected]
    await state.update_data(result=result)

    text = "Список активных игроков:\n\n"
    for idx, name in enumerate(selected):
        text += f"[{idx}] {name}\n"
    text += "\nЕсли нужно убрать игрока — введите его номер."

    await callback.message.answer(
        text,
        reply_markup=get_callback_btns(
            btns={"Выполнить": "perform", "Отменить всё": "cancel_activ"}, sizes=(2,)
        ),
    )
    await state.set_state(ActivControlFSM.id)


# ✅ Удалить игрока из списка
@admin_router.message(ActivControlFSM.id)
async def remove_player(message: types.Message, state: FSMContext):
    index = int(message.text)
    data = await state.get_data()
    selected = data.get("selected", [])

    if 0 <= index < len(selected):
        removed = selected.pop(index)
        await state.update_data(selected=selected)
        await message.answer(
            f"Игрок {removed} удалён. Введите ещё или нажмите кнопку.",
            reply_markup=get_callback_btns(
                btns={"Завершить": "+", "Отменить всё": "cancel_activ"}, sizes=(2,)
            ),
        )
        await state.set_state(ActivControlFSM.name)
    else:
        await message.answer("Некорректный номер игрока.")


# ✅ Выполнить операцию
@admin_router.callback_query(StateFilter(ActivControlFSM.id), F.data == "perform")
async def perform_control(
    callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    data = await state.get_data()
    await orm_update_player_plus(session, data["result"])
    await orm_update_player_minus(session, data["selected"])

    await state.clear()
    await callback.message.answer("Данные обновлены.", reply_markup=ADMIN_KB)
