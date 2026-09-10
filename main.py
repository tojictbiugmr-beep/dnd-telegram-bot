"""
D&D Telegram Bot — точка входа.
Стек: aiogram 3.x + SQLite + Groq AI + Narrative Director.
"""

import asyncio
import logging

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import config
from engine import Character, Dice, action_check, attack, STATS, STAT_NAMES
from db import Database
from ai import GroqAI
from director import GameDirector
from formatters import format_check, format_attack, format_character


class GameStates(StatesGroup):
    waiting_setting = State()


# ─── Логирование ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("dnd-bot")

# ─── Глобальные объекты ────────────────────────────────────
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database(config.DB_PATH)
ai = GroqAI(api_key=config.GROQ_API_KEY, model=config.GROQ_MODEL)

BUTTON_TEXTS = {"🎲 Бросок", "📋 Лист", "⚔️ Атака", "✨ Проверка",
                "💊 Лечить", "🗺 Сюжет", "🗣 NPC", "🎯 Квест"}


# ─── Клавиатуры ────────────────────────────────────────────

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Бросок"), KeyboardButton(text="📋 Лист")],
            [KeyboardButton(text="⚔️ Атака"), KeyboardButton(text="✨ Проверка")],
            [KeyboardButton(text="💊 Лечить"), KeyboardButton(text="🗺 Сюжет")],
            [KeyboardButton(text="🗣 NPC"), KeyboardButton(text="🎯 Квест")],
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
        builder.button(text=STAT_NAMES[s], callback_data=f"stat:{s}:{dc}")
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

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎲 **D&D Bot** — упрощённая D&D с режиссёрским движком\n\n"
        "Шаги старта:\n"
        "1. /setting — описать мир\n"
        "2. /create — создать персонажа\n\n"
        "Просто пишите текстом, что делаете — бот опишет результат.\n\n"
        "Команды:\n"
        "/check — проверка характеристики\n"
        "/attack — атака\n"
        "/roll — бросить кубики\n"
        "/heal — лечение\n"
        "/sheet — лист персонажа\n"
        "/plot — статус сюжета\n"
        "/npc — диалог с NPC\n"
        "/newgame — сброс сюжета\n",
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
    mod_str = f" {('+' + str(mod)) if mod >= 0 else str(mod)}" if mod else ""
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

    if dir_state["mode"] == "plot":
        text += f"\n\n🎭 PLOT (напряжение: {dir_state['tension']}/100)"

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


# ─── Сеттинг ─────────────────────────────────────────────

@dp.message(Command("setting"))
async def cmd_setting(message: Message, state: FSMContext):
    await state.clear()
    director = get_director(message.chat.id)
    if director.has_setting():
        info = director.get_setting_info()
        text = f"🌍 **Текущий сеттинг:**\n\n_{info['description']}_\n\n"
        if info["framework"]:
            text += f"**Каркас истории:**\n{info['framework']}\n\n"
        if director.milestones:
            text += "**Сюжетные цели:**\n"
            for i, ms in enumerate(director.milestones):
                tag = " ✅" if ms["completed"] else (" ←" if i == director.current_milestone_idx else "")
                text += f"  {i+1}. {ms['name']} ({ms['progress']}%){tag}\n"
        text += "\nХотите изменить? Опишите новый мир:"
    else:
        text = (
            "🌍 **Опишите ваш мир.**\n\n"
            "Например: «Мрачный мир, где солнце не взошло 100 лет, "
            "а древние культы пробуждаются в подземельях».\n\n"
            "Бот создаст сюжетные цели автоматически."
        )
    await state.set_state(GameStates.waiting_setting)
    await message.answer(text, parse_mode="Markdown")


@dp.message(GameStates.waiting_setting)
async def process_setting(message: Message, state: FSMContext):
    await state.clear()

    description = message.text
    director = get_director(message.chat.id)

    director.milestones = []
    director.current_milestone_idx = 0
    director.tension = 0
    director.milestone_proximity = 0
    director.player_history = []

    director.set_setting(description)
    save_director(message.chat.id, director)

    if ai.available:
        await message.answer("⏳ Генерирую мир и сюжетные цели...")
        try:
            framework = await ai.generate_framework(description)
            if framework:
                director.set_framework(framework)
                parsed = 0
                for line in framework.strip().split("\n"):
                    line = line.strip()
                    if not line or "|" not in line:
                        continue
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) < 2:
                        continue
                    name = parts[0]
                    ms_desc = parts[1]
                    actions = []
                    if len(parts) > 2 and parts[2]:
                        actions = [a.strip() for a in parts[2].split(",") if a.strip()]
                    director.add_milestone(name, ms_desc, actions)
                    parsed += 1

                save_director(message.chat.id, director)

                if parsed > 0:
                    text = f"🌍 **Мир создан!**\n\n_{description}_\n\n**Сюжетные цели ({parsed}):**\n"
                    for i, ms in enumerate(director.milestones):
                        text += f"  {i+1}. {ms['name']} — {ms['description']}\n"
                    text += "\nТеперь создайте персонажа: /create\nИ просто пишите текстом, что делаете."
                    await message.answer(text, parse_mode="Markdown")
                    return
                else:
                    save_director(message.chat.id, director)
                    await message.answer(
                        f"🌍 **Мир создан:**\n\n_{description}_\n\n"
                        f"**Каркас:**\n{framework}\n\n"
                        "(цели не распарсились — добавьте вручную: /quest)",
                        parse_mode="Markdown",
                    )
                    return
        except Exception as e:
            log.error(f"Framework generation error: {e}")

    await message.answer(
        f"🌍 **Мир создан:**\n\n_{description}_\n\n"
        "AI недоступен — добавьте цели вручную: /quest",
        parse_mode="Markdown",
    )


# ─── Квест и сюжет ───────────────────────────────────────

@dp.message(Command("quest"))
async def cmd_quest(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Формат: /quest <Название> | <Описание> | <ключевые слова>\n"
            "Пример: /quest Найти артефакт | Меч Древних в руинах | искать меч,руины"
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
    if director.has_setting():
        text += f"\n🌍 Сеттинг: {ctx['setting'][:100]}...\n"
    if ctx["framework"]:
        text += f"\n📜 Каркас: {ctx['framework'][:150]}...\n"
    if director.milestones:
        text += "\n_Все цели:_\n"
        for i, ms in enumerate(director.milestones):
            tag = " ✅" if ms["completed"] else (" ←" if i == director.current_milestone_idx else "")
            text += f"  {i+1}. {ms['name']} ({ms['progress']}%){tag}\n"

    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("newgame"))
async def cmd_newgame(message: Message):
    db.delete_director(message.chat.id)
    await message.answer("🎭 Сюжет сброшен. Начните заново: /setting")


@dp.message(Command("npc"))
async def cmd_npc(message: Message):
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
        await message.answer("💬 AI недоступен. Укажите GROQ_API_KEY.")


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
                       weapon="1d6", weapon_mod="dex")
    goblin.stats = {"str": 8, "dex": 14, "con": 10, "int": 10, "wis": 8, "cha": 8}
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
    stat = parts[1]
    dc = int(parts[2]) if len(parts) > 2 else 10
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
        "Формат: /quest <Название> | <Описание> | <ключевые слова>\n"
        "Пример: /quest Найти артефакт | Меч Древних в руинах | искать меч,руины"
    )


@dp.message(F.text == "🗣 NPC")
async def quick_npc(message: Message):
    await message.answer(
        "Формат: /npc <имя> <роль> <сообщение>\n"
        "Пример: /npc Боб трактирщик Привет!"
    )


# ─── Свободный ввод — игровое действие ───────────────────

@dp.message(F.text)
async def free_text_action(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return

    if message.text in BUTTON_TEXTS:
        return

    char = await get_char(message)
    if not char:
        return

    director = get_director(message.chat.id)

    if not director.has_setting():
        await message.answer("Сначала задайте сеттинг: /setting")
        return

    action = message.text
    dir_state = director.update_state(action)
    save_director(message.chat.id, director)

    if ai.available:
        try:
            narrative = await ai.generate_scene(action, director)
            text = narrative or "(пусто)"
        except Exception as e:
            text = f"(ошибка: {e})"
    else:
        text = (
            f"🎲 {action}\n"
            f"Режим: {dir_state['mode'].upper()}\n"
            f"Напряжение: {dir_state['tension']}/100\n"
            f"(AI недоступен — настройте GROQ_API_KEY)"
        )

    if dir_state["mode"] == "plot":
        text += f"\n\n🎭 PLOT (напряжение: {dir_state['tension']}/100)"

    await message.answer(text)


# ─── Запуск ───────────────────────────────────────────────

async def main():
    log.info("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
