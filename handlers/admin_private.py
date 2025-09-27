from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_add_card,
    orm_get_card,
    orm_get_cards,
    orm_get_players2,
    orm_update_card,
    orm_delete_card,
    orm_add_player,
    orm_change_player,
    orm_get_player,
    orm_get_players,
    orm_delete_player,
    orm_update_player_minus,
    orm_update_player_plus,
    orm_change_status_player,
    orm_get_status,
)

from filters.chat_types import ChatTypeFilter, IsAdmin

from kbds.inline import get_callback_btns
from kbds.reply import get_keyboard, del_reply_kd


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


ADMIN_KB = get_keyboard(
    "Карточки",
    "Игроки",
    "Отчёты",
    "Контроль",
    placeholder="Выберите действие",
    sizes=(2, 2),
)

################################# Админ команды #################################


@admin_router.message(Command("admin"))
async def admin_on(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)


@admin_router.message(Command("off"))
async def admin_off(message: types.Message):
    await message.answer("Админ клавиатура удалена", reply_markup=del_reply_kd)


@admin_router.message(F.text == "Карточки")
async def admin_cards(message: types.Message):
    await message.answer(
        "Существует несколько команд для работы с карточками, чтобы создать новую карточку или просмотреть список существующих, нажмите на нужную кнопку. "
        "Для просмотра конкретной карточки введите card_[название карточки]",
        reply_markup=get_callback_btns(
            btns={
                "Новая карточка": "add-new-card",
                "Список карточек": "card-list",
            },
            sizes=(2,),
        ),
    )


@admin_router.message(F.text == "Игроки")
async def admin_players(message: types.Message):
    await message.answer(
        "Существует несколько команд для работы с игроками, чтобы добавить нового игрока или просмотреть список существующих, нажмите на нужную кнопку."
        "Для просмотра конкретного игрока введите player_[позывной игрока]",
        reply_markup=get_callback_btns(
            btns={
                "Новый игрок": "add-new-player",
                "Список игроков": "players-list",
            },
            sizes=(2,),
        ),
    )


@admin_router.message(F.text == "Отчёты")
async def admin_reports(message: types.Message):
    await message.answer(
        "Выберите вариант",
        reply_markup=get_callback_btns(
            btns={
                "Норма": f"report_{1}",
                "Отпуска": f"report_{2}",
                "Казнь": f"report_{3}",
            },
            sizes=(1, 2),
        ),
    )


################################################################################################
################################# Админ команды ( карточки ) #################################


# Получение списка карточек
@admin_router.callback_query(F.data == "card-list")
async def list_of_cards(callback: types.CallbackQuery, session: AsyncSession):
    cards = await orm_get_cards(session)
    if not cards:
        await callback.message.answer("Список карточек пуст.")
        return

    text = "\n".join(card.name for card in cards)
    await callback.message.answer(f"Вот список карточек:\n\n{text}")


# Просмотр карточки по имени
@admin_router.message(F.text.startswith("card_"))
async def card_show(message: types.Message, session: AsyncSession):
    name = message.text.removeprefix("card_")
    card = await orm_get_card(session, name)

    if not card:
        await message.answer(f"Карточка с именем '{name}' не найдена.")
        return

    keyboard = get_callback_btns(
        btns={
            "Редактировать": f"change-сard_{card.name}",
            "Удалить": f"delete_{card.name}",
        },
        sizes=(2,),
    )

    await message.answer_photo(
        photo=card.image,
        caption=card.name,
        reply_markup=keyboard,
    )


# Инициализация добавления карточки (FSM)
@admin_router.callback_query(F.data == "add-new-card")
async def add_card(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AddCard.name)
    await callback.message.answer(
        "Введите название техники",
        reply_markup=types.ReplyKeyboardRemove(),
    )


# Удаление карточки
@admin_router.callback_query(F.data.startswith("delete_"))
async def delete_card(callback: types.CallbackQuery, session: AsyncSession):
    name = callback.data.removeprefix("delete_")
    success = await orm_delete_card(session, name)

    if success:
        await callback.message.answer(f"Карточка '{name}' удалена.")
    else:
        await callback.message.answer(f"Карточка '{name}' не найдена или не удалена.")


@admin_router.callback_query(F.data.startswith("change-card_"))
async def start_edit_card(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    name = callback.data.split("_")[-1]
    card = await orm_get_card(session, name)
    await state.update_data(item_for_change=card, original_key=name)
    await callback.message.answer("Введите новое название карточки:")
    await state.set_state(AddCard.name)



################################# Админ команды (игроки) #################################


# Получение списка игроков
@admin_router.callback_query(F.data == "players-list")
async def list_of_players(callback: types.CallbackQuery, session: AsyncSession):
    players = await orm_get_players(session)

    if not players:
        await callback.message.answer("Список игроков пуст.")
        return

    text = "\n".join(player.name for player in players)
    await callback.message.answer(f"Вот список игроков:\n\n{text}")


# Просмотр информации об игроке
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


# Инициализация добавления нового игрока (FSM)
@admin_router.callback_query(F.data == "add-new-player")
async def add_new_player(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AddUser.name)
    await callback.message.answer("Введите позывной", reply_markup=types.ReplyKeyboardRemove())


# Изменение позывного игрока (FSM)
@admin_router.callback_query(F.data.startswith("change-player_"))
async def change_player_name(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    player_name = callback.data.removeprefix("change-player_")
    player = await orm_get_player(session, player_name)

    if not player:
        await callback.message.answer(f"Игрок '{player_name}' не найден.")
        return

    AddUser.user_for_change = player
    AddUser.player_name = player_name

    await state.set_state(AddUser.name)
    await callback.message.answer("Введите новый позывной", reply_markup=types.ReplyKeyboardRemove())


# Изменение статуса игрока (переключение)
@admin_router.callback_query(F.data.startswith("change-status_"))
async def change_player_status(callback: types.CallbackQuery, session: AsyncSession):
    player_name = callback.data.removeprefix("change-status_")
    player = await orm_get_player(session, player_name)

    if not player:
        await callback.message.answer(f"Игрок '{player_name}' не найден.")
        return

    # Переключение между статусами 1 и 2
    new_status = 2 if player.statuses_id == 1 else 1
    await orm_change_status_player(session, player_name, new_status)

    await callback.answer("Статус обновлён")


# Удаление игрока
@admin_router.callback_query(F.data.startswith("delete-player_"))
async def delete_player(callback: types.CallbackQuery, session: AsyncSession):
    player_name = callback.data.removeprefix("delete-player_")
    success = await orm_delete_player(session, player_name)

    if success:
        await callback.message.answer(f"Игрок '{player_name}' удалён.")
    else:
        await callback.message.answer(f"Игрок '{player_name}' не найден или не удалён.")


@admin_router.callback_query(F.data.startswith("change-user_"))
async def start_edit_user(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    name = callback.data.split("_")[-1]
    user = await orm_get_user(session, name)
    await state.update_data(item_for_change=user, original_key=name)
    await callback.message.answer("Введите новый позывной:")
    await state.set_state(AddUser.name)


################################# Админ команды (универсальный FSM) #################################


class AddCard(StatesGroup):
    name = State()
    image = State()

    text = {
        "AddCard:name": "Введите название заново:",
        "AddCard:image": "Отправьте изображение карточки.",
    }


class AddUser(StatesGroup):
    name = State()

    text = {
        "AddUser:name": "Введите позывной игрока:",
    }


################################# Админ команды (универсальный FSM (отмена/назад)) #################################


@admin_router.message(StateFilter("*"), Command("отмена"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("Действие отменено", reply_markup=ADMIN_KB)


@admin_router.message(StateFilter("*"), Command("назад"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "назад")
async def back_step_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if not current_state:
        return

    all_states = AddCard.__all_states__ + AddUser.__all_states__
    previous = None
    for step in all_states:
        if step.state == current_state:
            if previous:
                await state.set_state(previous)
                state_texts = getattr(step.group, "text", {})
                text = state_texts.get(previous.state, "Вы вернулись назад.")
                await message.answer(text)
            else:
                await message.answer("Вы уже на первом шаге.")
            return
        previous = step


# универсальный хендлер name
@admin_router.message(F.text, StateFilter(AddCard.name, AddUser.name))
async def handle_name_input(message: types.Message, state: FSMContext, session: AsyncSession):
    state_name = await state.get_state()
    state_group = AddCard if state_name.startswith("AddCard") else AddUser

    text = message.text.strip()
    if not (3 <= len(text) <= 150):
        await message.answer("Текст должен быть от 3 до 150 символов.")
        return

    await state.update_data(name=text)


    if state_group is AddCard:
        await message.answer(state_group.text.get(f"{state_group.__name__}:image", "Введите следующий шаг."))
        await state.set_state(AddCard.image)
    else:
        # Финальный шаг — сразу сохраняем
        await save_entity(state_group, message, state, session)


# хэендлер image
@admin_router.message(AddCard.image, or_f(F.photo, F.text == "."))
async def handle_card_image(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    elif message.text == ".":
        data = await state.get_data()
        if "item_for_change" in data:
            await state.update_data(image=data["item_for_change"].get("image"))
    else:
        await message.answer("Отправьте изображение карточки.")
        return

    await save_entity(AddCard, message, state, session)


# общая функция сохранения
async def save_entity(state_group, message: types.Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    item_for_change = data.get("item_for_change")
    original_key = data.get("original_key")

    try:
        if item_for_change:
            if state_group is AddCard:
                await orm_update_card(session, original_key, data)
            elif state_group is AddUser:
                await orm_change_player(session, original_key, data)
        else:
            if state_group is AddCard:
                await orm_add_card(session, data)
            elif state_group is AddUser:
                await orm_add_player(session, data)

        await message.answer("Данные успешно сохранены.", reply_markup=ADMIN_KB)
    except IntegrityError:
        await message.answer("Объект с такими данными уже существует.")
        return
    except Exception as e:
        await message.answer(f"Ошибка при сохранении: {e}")
    finally:
        await state.clear()


############################################################################################
################# Команды для отчётности ############################


@admin_router.callback_query(F.data.startswith("report_"))
async def report_cmd(callback: types.CallbackQuery, session: AsyncSession):
    try:
        status_id = int(callback.data.removeprefix("report_"))
    except ValueError:
        await callback.message.answer("Неверный формат команды.")
        return


    # Получение статуса
    status = await orm_get_status(session, status_id)
    header = f"📝 Отчёт по личному составу Триозёрска\nСтатус: {status.name}\n\n"

    # Получение игроков с данным статусом
    players = await orm_get_players(session, status_id)
    if not players:
        await callback.message.answer(header + "Нет игроков с этим статусом.")
        return

    # Формирование списка игроков
    players_list = "\n".join(
        f"{player.name} | {player.count} | {player.direction.name}" for player in players
    )

    await callback.message.answer(header + players_list)



################# FSM для выполнения актив контроля ############################


class ActivControlFSM(StatesGroup):
    name = State()
    id = State()

# ✅ Старт команды "Контроль"
@admin_router.message(F.text == "Контроль")
async def start_control(message: types.Message, state: FSMContext, session: AsyncSession):
    players = await orm_get_players2(session)
    await state.update_data(all_players=players, selected=[], result=[])

    await message.answer(
        "Введите позывной активного игрока", 
        reply_markup=types.ReplyKeyboardRemove()
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
                btns={"Завершить": "+", "Отменить всё": "cancel_activ"},
                sizes=(2,)
            )
        )
    else:
        await message.answer("Такого игрока нет в базе или он в отпуске.")


# ✅ Показать список и предложить удалить
@admin_router.callback_query(F.data == "+")
async def show_selected(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
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
            btns={"Выполнить": "perform", "Отменить всё": "cancel_activ"},
            sizes=(2,)
        )
    )
    await state.set_state(ActivControlFSM.id)


# ✅ Удалить игрока из списка
@admin_router.message(ActivControlFSM.id, F.text.regexp(r"^\d+$"))
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
                btns={"Завершить": "+", "Отменить всё": "cancel_activ"},
                sizes=(2,)
            )
        )
        await state.set_state(ActivControlFSM.name)
    else:
        await message.answer("Некорректный номер игрока.")


# ✅ Выполнить операцию
@admin_router.callback_query(StateFilter(ActivControlFSM.id), F.data == "perform")
async def perform_control(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await orm_update_player_plus(session, data["result"])
    await orm_update_player_minus(session, data["selected"])

    await state.clear()
    await callback.message.answer("Данные обновлены.", reply_markup=ADMIN_KB)