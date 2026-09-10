"""
D&D Telegram Bot — точка входа
Стек: aiogram 3.x + SQLite + Groq AI + Dual-Mode Narrative Director
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from engine import (
    Character, Dice, action_check, attack, roll_initiative,
    STATS, STAT_NAMES,
)
from db import Database
from ai import GroqAI
from director import GameDirector
from formatters import format_check, format_attack, format_character

# ─── Логирование ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("dnd-bot")

# ─── Глобальные объекты ────────────────────────────────────
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()
db = Database(config.DB_PATH)
ai = GroqAI(api_key=config.GROQ_API_KEY, model=config.GROQ_MODEL)


# ─── Клавиатуры ────────────────────────────────────────────
def setting_select_kb() -> InlineKeyboardMarkup:
    """Inline-кнопки выбора сеттинга."""
    builder = InlineKeyboardBuilder()
    presets = GameDirector.PRESET_SETTINGS
    for key, val in presets.items():
        builder.button(text=val["name"], callback_data=f"setting:{key}")
    builder.button(text="✏️ Свой", callback_data="setting:custom")
    builder.adjust(2)
    return builder.as_markup()
    
def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Бросок"), KeyboardButton(text="📋 Лист")],
            [KeyboardButton(text="⚔️ Атака"), KeyboardButton(text="✨ Проверка")],
            [KeyboardButton(text="💊 Лечить"), KeyboardButton(text="🗺 Сюжет")],
            [KeyboardButton(text="🌍 Сеттинг"), KeyboardButton(text="🎯 Квест")],
            [KeyboardButton(text="🗣 NPC"), KeyboardButton(text="🎬 Действие")],
        ],
        resize_keyboard=True,
    )



def class_select_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, label in [
        ("fighter", "⚔️ Воин"),
        ("rogue", "🗡 Плут"),
        ("wizard", "🔮 Волшебник"),
        ("cleric", "🙏 Жрец"),
    ]:
        builder.button(text=label, callback_data=f"create:{key}")
    builder.adjust(2)
    return builder.as_markup()


def stat_select_kb(dc: int = 10) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in STATS:
        builder.button(text=STAT_NAMES[s], callback_data=f"stat:check:{s}:{dc}")
    builder.adjust(3)
    return builder.as_markup()


# ─── Хелперы ──────────────────────────────────────────────

async def get_char(message: Message) -> Character | None:
    char = db.get_character(message.from_user.id)
    if char is None:
        await message.answer("У вас нет персонажа. Создайте: /create")
    return char


def get_director(chat_id: int) -> GameDirector:
    return db.get_director(chat_id)


def save_director(chat_id: int, director: GameDirector) -> None:
    db.save_director(chat_id, director)


# ─── Команды ──────────────────────────────────────────────
@dp.message(Command("setting"))
async def cmd_setting(message: Message):
    """Выбор сеттинга мира."""
    director = get_director(message.chat.id)
    current = director.get_setting_info()

    text = "🌍 **Выбор сеттинга мира**\n\n"
    if director.has_setting():
        text += f"Текущий: **{current['name']}**\n"
        text += f"_{current['description']}_\n\n"
        text += "Выберите новый или задайте свой:"
    else:
        text += "Сеттинг не задан. Выберите пресет или задайте свой:"

    await message.answer(text, parse_mode="Markdown",
                         reply_markup=setting_select_kb())


@dp.callback_query(F.data.startswith("setting:"))
async def cb_setting(callback: CallbackQuery):
    """Обработка выбора сеттинга."""
    key = callback.data.split(":")[1]
    director = get_director(callback.message.chat.id)

    if key == "custom":
        await callback.message.edit_text(
            "✏️ Напишите свой сеттинг командой:\n"
            "`/setcustom Название и описание вашего мира`\n\n"
            "Пример: `/setcustom Мир ледяных пустошей, где солнце не взошло 100 лет`"
        )
        await callback.answer()
        return

    success = director.set_setting(key=key)
    if success:
        save_director(callback.message.chat.id, director)
        info = director.get_setting_info()
        await callback.message.edit_text(
            f"🌍 **Сеттинг установлен: {info['name']}**\n\n"
            f"_{info['description']}_\n\n"
            f"Тон: {info['tone']}\n"
            f"Темы: {info['themes']}\n\n"
            f"Теперь добавьте сюжетную цель: /quest",
            parse_mode="Markdown",
        )
        await callback.answer("Готово!")
    else:
        await callback.answer("Ошибка: неизвестный сеттинг")


@dp.message(Command("setcustom"))
async def cmd_setcustom(message: Message):
    """Задать кастомный сеттинг. Формат: /setcustom описание мира"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Формат: /setcustom <описание мира>\n"
            "Пример: /setcustom Мир ледяных пустошей, солнце не взошло 100 лет"
        )
        return

    director = get_director(message.chat.id)
    director.set_setting(custom=args[1])
    save_director(message.chat.id, director)

    await message.answer(
        f"🌍 **Сеттинг установлен: Свой сеттинг**\n\n"
        f"_{args[1]}_\n\n"
        f"Теперь добавьте сюжетную цель: /quest",
        parse_mode="Markdown",
    )


@dp.message(F.text == "🌍 Сеттинг")
async def quick_setting(message: Message):
    """Кнопка быстрого выбора сеттинга."""
    director = get_director(message.chat.id)
    current = director.get_setting_info()

    text = "🌍 **Сеттинг мира**\n\n"
    if director.has_setting():
        text += f"Текущий: **{current['name']}**\n"
        text += f"_{current['description']}_\n\n"
        text += "Изменить:"
    else:
        text += "Не задан. Выберите:"

    await message.answer(text, parse_mode="Markdown",
                         reply_markup=setting_select_kb())


@dp.message(F.text == "🎬 Действие")
async def quick_act(message: Message):
    """Кнопка-подсказка для свободного действия."""
    await message.answer(
        "Опишите действие: /act <что делаете>\n"
        "Пример: /act осматриваю руины замка"
        )
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎲 **D&D Bot** — упрощённая D&D с режиссёрским движком\n\n"
        "Команды:\n"
        "/create — создать персонажа\n"
        "/roll `d20` — бросить кубики\n"
        "/check — проверка характеристики\n"
        "/attack — атака по цели\n"
        "/heal — вылечить\n"
        "/sheet — лист персонажа\n"
        "/quest — добавить сюжетную цель\n"
        "/plot — статус сюжета (milestone, tension, режим)\n"
        "/npc — поговорить с NPC\n"
        "/act — свободное действие (режиссёр опишет результат)\n"
        "/newgame — сбросить сюжет\n",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )


@dp.message(Command("create"))
async def cmd_create(message: Message):
    char = db.get_character(message.from_user.id)
    if char is not None:
        await message.answer(
            f"У вас уже есть персонаж: {char.name}. "
            f"Удалите через /delete, чтобы создать нового."
        )
        return
    await message.answer("Выберите класс:", reply_markup=class_select_kb())


@dp.callback_query(F.data.startswith("create:"))
async def cb_create(callback: CallbackQuery):
    class_key = callback.data.split(":")[1]
    char = Character.quick_create(
        name=callback.from_user.first_name or "Герой",
        class_key=class_key,
        level=1,
    )
    db.save_character(callback.from_user.id, char)
    await callback.message.edit_text(format_character(char), parse_mode="HTML")
    await callback.answer("Готово!")


@dp.message(Command("delete"))
async def cmd_delete(message: Message):
    db.delete_character(message.from_user.id)
    await message.answer("Персонаж удалён. Создайте нового: /create")


@dp.message(Command("sheet"))
async def cmd_sheet(message: Message):
    char = await get_char(message)
    if char:
        await message.answer(format_character(char), parse_mode="HTML")


@dp.message(Command("roll"))
async def cmd_roll(message: Message):
    char = await get_char(message)
    if not char:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Формат: /roll 2d6+3")
        return
    spec = args[1]
    try:
        result = Dice.roll(spec)
    except Exception:
        await message.answer("Не понял формат. Пример: /roll d20 или /roll 2d6+3")
        return
    rolls_str = " + ".join(str(r) for r in result["rolls"])
    mod = result["mod"]
    mod_str = f" {('+'+str(mod)) if mod >= 0 else str(mod)}" if mod else ""
    text = f"🎲 {spec}: {rolls_str}{mod_str} = **{result['total']}**"
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("check"))
async def cmd_check(message: Message):
    char = await get_char(message)
    if not char:
        return
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "Формат: /check <хар-ка> <DC>\n"
            "Пример: /check str 15\n"
            "Хар-ки: str dex con int wis cha"
        )
        return
    stat = args[1].lower()
    if stat not in STATS:
        await message.answer(f"Нет такой. Доступны: {', '.join(STATS)}")
        return
    try:
        dc = int(args[2])
    except ValueError:
        await message.answer("DC должен быть числом. Пример: /check str 15")
        return

    result = action_check(char, stat, dc)
    text = format_check(result)

    # Режиссёр: обновляем состояние
    director = get_director(message.chat.id)
    dir_state = director.update_state(f"проверка {stat}", result)
    save_director(message.chat.id, director)

    if ai.available:
        try:
            narrative = await ai.narrate_check(result, director)
            if narrative:
                text += f"\n\n_{narrative}_"
        except Exception:
            pass

    # Показываем режим, если Plot
    if dir_state["mode"] == "plot":
        text += f"\n\n🎭 Режим: PLOT (напряжение: {dir_state['tension']}/100)"

    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("attack"))
async def cmd_attack(message: Message):
    char = await get_char(message)
    if not char:
        return
    args = message.text.split()
    if len(args) < 4:
        await message.answer(
            "Формат: /attack <имя> <AC> <HP>\n"
            "Пример: /attack Гоблин 12 15"
        )
        return
    target_name = args[1]
    try:
        target_ac = int(args[2])
        target_hp = int(args[3])
    except ValueError:
        await message.answer("AC и HP — числа. Пример: /attack Гоблин 12 15")
        return

    target = Character(
        name=target_name, ac=target_ac,
        max_hp=target_hp, current_hp=target_hp,
    )
    result = attack(char, target)
    text = format_attack(result)

    # Режиссёр
    director = get_director(message.chat.id)
    dir_state = director.update_state(f"атакую {target_name}")
    save_director(message.chat.id, director)

    if ai.available:
        try:
            narrative = await ai.narrate_attack(result, director)
            if narrative:
                text += f"\n\n_{narrative}_"
        except Exception:
            pass

    db.save_character(message.from_user.id, char)
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("heal"))
async def cmd_heal(message: Message):
    char = await get_char(message)
    if not char:
        return
    args = message.text.split()
    if len(args) > 1:
        try:
            amount = int(args[1])
        except ValueError:
            amount = Dice.roll("1d4")["total"]
    else:
        amount = Dice.roll("1d4")["total"]

    new_hp = char.heal(amount)
    db.save_character(message.from_user.id, char)
    await message.answer(
        f"💊 {char.name} восстанавливает {amount} HP. "
        f"Текущее HP: {new_hp}/{char.max_hp}"
    )


# ─── Новые команды: режиссёр ─────────────────────────────

@dp.message(Command("quest"))
async def cmd_quest(message: Message):
    """Добавить milestone. Формат: /quest Название | Описание | действие1,действие2"""
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Формат: /quest <Название> | <Описание> | <ключевые действия>\n"
            "Пример: /quest Найти артефакт | Отыскать Меч Древних | искать артефакт,найти меч"
        )
        return
    parts = args[1].split("|")
    if len(parts) < 2:
        await message.answer("Нужно: Название | Описание | действия")
        return
    name = parts[0].strip()
    description = parts[1].strip()
    target_actions = []
    if len(parts) > 2:
        target_actions = [a.strip() for a in parts[2].split(",")]

    director = get_director(message.chat.id)
    director.add_milestone(name, description, target_actions)
    save_director(message.chat.id, director)

    await message.answer(
        f"🎯 Сюжетная цель добавлена:\n"
        f"   {name}\n"
        f"   {description}\n"
        f"   Ключевые действия: {', '.join(target_actions) if target_actions else 'нет'}"
    )


@dp.message(Command("plot"))
async def cmd_plot(message: Message):
    """Показать статус сюжета."""
    director = get_director(message.chat.id)
    ctx = director.get_context()

    text = (
        f"🎭 **Статус сюжета**\n\n"
        f"Режим: **{ctx['mode'].upper()}**\n"
        f"Текущая цель: {ctx['current_milestone']}\n"
        f"Прогресс: {ctx['milestone_progress']}%\n"
        f"Описание: {ctx['milestone_description']}\n"
        f"Напряжение: {ctx['tension']}/100\n"
        f"Близость к цели: {ctx['proximity']}%\n"
    )
    if director.milestones:
        text += "\n_all Milestones:_\n"
        for i, ms in enumerate(director.milestones):
            tag = " ✅" if ms["completed"] else (" ←" if i == director.current_milestone_idx else "")
            text += f"  {i+1}. {ms['name']} ({ms['progress']}%){tag}\n"

    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("act"))
async def cmd_act(message: Message):
    """Свободное действие игрока — режиссёр опишет результат."""
    char = await get_char(message)
    if not char:
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Опишите действие: /act иду осмотреть руины")
        return
    action = args[1]

    director = get_director(message.chat.id)
    dir_state = director.update_state(action)
    save_director(message.chat.id, director)

    text = ""
    if ai.available:
        try:
            narrative = await ai.narrate_action(action, director)
            if narrative:
                text = narrative
        except Exception as e:
            text = f"(ошибка: {e})"
    else:
        text = f"🎲 Действие: {action}\nРежим: {dir_state['mode'].upper()}"

    if dir_state["mode"] == "plot":
        text += f"\n\n🎭 PLOT (напряжение: {dir_state['tension']}/100)"

    await message.answer(text)


@dp.message(Command("newgame"))
async def cmd_newgame(message: Message):
    """Сбросить сюжетное состояние."""
    db.delete_director(message.chat.id)
    await message.answer("🎭 Сюжет сброшен. Добавьте новую цель: /quest")


@dp.message(Command("npc"))
async def cmd_npc(message: Message):
    """Диалог с NPC. Формат: /npc <имя> <роль> <сообщение>"""
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "Формат: /npc <имя_NPC> <роль> <сообщение>\n"
            "Пример: /npc Боб трактирщик Что поесть?"
        )
        return
    npc_name = args[1]
    msg_parts = args[2].split(maxsplit=1)
    if len(msg_parts) == 2:
        npc_role = msg_parts[0]
        user_msg = msg_parts[1]
    else:
        npc_role = "NPC"
        user_msg = msg_parts[0]

    director = get_director(message.chat.id)

    if ai.available:
        try:
            reply = await ai.npc_dialogue(npc_name, npc_role, user_msg, director)
            await message.answer(f"🗣 {npc_name}:\n{reply}")
        except Exception as e:
            await message.answer(f"NPC молчит... (ошибка: {e})")
    else:
        await message.answer(
            "💬 AI недоступен. Укажите GROQ_API_KEY в переменных окружения."
        )


# ─── Быстрые кнопки ───────────────────────────────────────

@dp.message(F.text == "🎲 Бросок")
async def quick_roll(message: Message):
    char = await get_char(message)
    if not char:
        return
    result = Dice.d20(mod=0)
    await message.answer(
        f"🎲 d20: {result['natural']} = **{result['total']}**",
        parse_mode="Markdown",
    )


@dp.message(F.text == "📋 Лист")
async def quick_sheet(message: Message):
    char = await get_char(message)
    if char:
        await message.answer(format_character(char), parse_mode="HTML")


@dp.message(F.text == "⚔️ Атака")
async def quick_attack(message: Message):
    char = await get_char(message)
    if not char:
        return
    goblin = Character(name="Гоблин", ac=12, max_hp=7, current_hp=7,
                       dex=14, weapon="1d6", weapon_mod="dex")
    result = attack(char, goblin)
    text = format_attack(result)

    director = get_director(message.chat.id)
    director.update_state("атакую гоблина")
    save_director(message.chat.id, director)

    if ai.available:
        try:
            narrative = await ai.narrate_attack(result, director)
            if narrative:
                text += f"\n\n_{narrative}_"
        except Exception:
            pass

    db.save_character(message.from_user.id, char)
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "✨ Проверка")
async def quick_check(message: Message):
    char = await get_char(message)
    if not char:
        return
    await message.answer(
        "Выберите характеристику (DC = 10):",
        reply_markup=stat_select_kb(10),
    )


@dp.callback_query(F.data.startswith("stat:"))
async def cb_stat_check(callback: CallbackQuery):
    parts = callback.data.split(":")
    stat = parts[2]
    dc = int(parts[3]) if len(parts) > 3 else 10
    char = db.get_character(callback.from_user.id)
    if not char:
        await callback.answer("Сначала создайте: /create")
        return
    result = action_check(char, stat, dc)
    text = format_check(result)

    director = get_director(callback.message.chat.id)
    dir_state = director.update_state(f"проверка {stat}", result)
    save_director(callback.message.chat.id, director)

    if ai.available:
        try:
            narrative = await ai.narrate_check(result, director)
            if narrative:
                text += f"\n\n_{narrative}_"
        except Exception:
            pass

    if dir_state["mode"] == "plot":
        text += f"\n\n🎭 PLOT (напряжение: {dir_state['tension']}/100)"

    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


@dp.message(F.text == "💊 Лечить")
async def quick_heal(message: Message):
    char = await get_char(message)
    if not char:
        return
    amount = Dice.roll("1d4")["total"]
    new_hp = char.heal(amount)
    db.save_character(message.from_user.id, char)
    await message.answer(
        f"💊 {char.name} выпивает зелье. Восстановлено {amount} HP. "
        f"Текущее HP: {new_hp}/{char.max_hp}"
    )


@dp.message(F.text == "🗺 Сюжет")
async def quick_plot(message: Message):
    """Кнопка быстрого просмотра статуса сюжета."""
    director = get_director(message.chat.id)
    ctx = director.get_context()

    text = (
        f"🎭 **Статус сюжета**\n\n"
        f"Режим: **{ctx['mode'].upper()}**\n"
        f"Текущая цель: {ctx['current_milestone']}\n"
        f"Прогресс: {ctx['milestone_progress']}%\n"
        f"Напряжение: {ctx['tension']}/100\n"
        f"Близость: {ctx['proximity']}%\n"
    )
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "🎯 Квест")
async def quick_quest(message: Message):
    await message.answer(
        "Формат: /quest <Название> | <Описание> | <ключевые действия>\n"
        "Пример: /quest Найти артефакт | Меч Древних | искать артефакт,найти меч"
    )


@dp.message(F.text == "🗣 NPC")
async def quick_npc(message: Message):
    await message.answer(
        "Формат: /npc <имя> <роль> <сообщение>\n"
        "Пример: /npc Боб трактирщик Привет!"
    )


# ─── Запуск ───────────────────────────────────────────────

async def main():
    log.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    

