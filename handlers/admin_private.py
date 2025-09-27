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
                "Общее": f"report_{1}",
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


################################# Админ команды (FSM для карточек) #################################


class AddCard(StatesGroup):
    name = State()
    image = State()

    card_for_change = None

    text = {
        "AddCard:name": "Введите название заново:",
        "AddCard:image": "Этот стейт последний, поэтому...",
    }


# запуск FSM добавления карточек, становимся в ожидание name (редактирование)
@admin_router.callback_query(StateFilter(None), F.data.startswith("change-сard_"))
async def change_card(
    callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    name = callback.data.split("_")[-1]
    card_for_change = await orm_get_card(session, name)

    AddCard.card_for_change = card_for_change

    await callback.answer()
    await callback.message.answer(
        "Введите название техникиа", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddCard.name)


# Хендлер отмены и сброса состояния должен быть всегда именно здесь,
# после того, как только встали в состояние номер 1 (элементарная очередность фильтров)
@admin_router.message(StateFilter("*"), Command("отмена"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddCard.card_for_change:
        AddCard.card_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


# Вернутся на шаг назад (на прошлое состояние)
@admin_router.message(StateFilter("*"), Command("назад"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "назад")
async def back_step_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddCard.name:
        await message.answer(
            'Предидущего шага нет, или введите название техники или напишите "отмена"'
        )
        return

    previous = None
    for step in AddCard.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(
                f"Ок, вы вернулись к прошлому шагу \n {AddCard.texts[previous.state]}"
            )
            return
        previous = step


# Ловим данные для состояние name и потом меняем состояние на image
@admin_router.message(AddCard.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == "." and AddCard.card_for_change:
        await state.update_data(name=AddCard.card_for_change.name)
    else:
        # Здесь можно сделать какую либо дополнительную проверку
        # и выйти из хендлера не меняя состояние с отправкой соответствующего сообщения
        # например:
        if 3 >= len(message.text) >= 150:
            await message.answer(
                "Название карточки не должно превышать 150 символов\nили быть менее трёх символов. \n Введите заново"
            )
            return

        await state.update_data(name=message.text)
    await message.answer("Отправьте карточку")
    await state.set_state(AddCard.image)


# Хендлер для отлова некорректных вводов для состояния name
@admin_router.message(AddCard.name)
async def add_name2(message: types.Message):
    await message.answer(
        "Вы ввели не допустимые данные, введите текст названия техники"
    )


# Ловим данные для состояние image и потом выходим из состояний
@admin_router.message(AddCard.image, or_f(F.photo, F.text == "."))
async def add_image(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text == "." and AddCard.card_for_change:
        await state.update_data(image=AddCard.card_for_change.image)
    elif message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    else:
        await message.answer("Отправьте карточку в виде картинки")
        return
    data = await state.get_data()
    try:
        if AddCard.card_for_change:
            await orm_update_card(session, AddCard.card_for_change.name, data)

        else:
            print(1)
            await orm_add_card(session, data)
        await message.answer("Карточка добавлена/изменена", reply_markup=ADMIN_KB)
        await state.clear()

    except Exception as e:
        await message.answer(
            f"Ошибка: \n{str(e)}\nОбратись к программеру, он опять денег хочет",
            reply_markup=ADMIN_KB,
        )
        await state.clear()

    AddCard.card_for_change = None


# Ловим все прочее некорректное поведение для этого состояния
@admin_router.message(AddCard.image)
async def add_image2(message: types.Message):
    await message.answer("Отправьте фото карточки бронепробития")


############################################################################################
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


################################# Админ команды (FSM для игроков) #################################


class AddUser(StatesGroup):
    name = State()

    player_name = None
    user_for_change = None

    text = {
        "AddCard:name": "Введите позывной игрока:",
    }


# Хендлер отмены и сброса состояния должен быть всегда именно здесь,
# после того, как только встали в состояние номер 1 (элементарная очередность фильтров)
@admin_router.message(StateFilter("*"), Command("отмена"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "отмена")
async def cancel_handler_user(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddUser.user_for_change:
        AddUser.user_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


# Ловим данные для состояние name и потом сохраняем
@admin_router.message(AddUser.name, F.text)
async def add_user_ame(
    message: types.Message, state: FSMContext, session: AsyncSession
):
    # Здесь можно сделать какую либо дополнительную проверку
    # и выйти из хендлера не меняя состояние с отправкой соответствующего сообщения
    # например:
    if 3 >= len(message.text) <= 25:
        await message.answer(
            "Позывной игрока должен быть больше 2 и меньше 25 символов. \n Введите заново"
        )
        return

    await state.update_data(name=message.text)
    data = await state.get_data()

    try:
        if AddUser.user_for_change:
            await orm_change_player(session, AddUser.player_name, data)

        else:
            await orm_add_player(session, data)

        await state.clear()
        await message.answer("Игрок добавлен", reply_markup=ADMIN_KB)

    except IntegrityError:
        await message.answer(
            "Игрок с таким позывным уже есть, введите другой позывной",
            reply_markup=ADMIN_KB,
        )
        return


# Хендлер для отлова некорректных вводов для состояния name
@admin_router.message(AddUser.name)
async def add_user_name2(message: types.Message):
    await message.answer("Вы ввели не допустимые данные, введите позывной игрока")


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