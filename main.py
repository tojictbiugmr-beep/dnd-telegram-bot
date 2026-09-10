"""
D&D Telegram Bot — точка входа
Стек: aiogram 3.x + SQLite + Groq AI
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

def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню — быстрые действия."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎲 Бросок"), KeyboardButton(text="📋 Лист")],
            [KeyboardButton(text="⚔️ Атака"), KeyboardButton(text="✨ Проверка")],
            [KeyboardButton(text="💊 Лечить"), KeyboardButton(text="🗣 NPC")],
        ],
        resize_keyboard=True,
    )


def class_select_kb() -> InlineKeyboardMarkup:
    """Выбор класса при создании персонажа."""
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
    """Выбор характеристики для проверки."""
    builder = InlineKeyboardBuilder()
    for s in STATS:
        builder.button(text=STAT_NAMES[s], callback_data=f"stat:check:{s}:{dc}")
    builder.adjust(3)
    return builder.as_markup()


# ─── Хелперы ──────────────────────────────────────────────

async def get_or_warn(message: Message) -> Character | None:
    """Получить персонажа пользователя или предупредить."""
    char = db.get_character(message.from_user.id)
    if char is None:
        await message.answer("У вас нет персонажа. Создайте: /create")
    return char


# ─── Команды ──────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🎲 **D&D Bot** — упрощённая D&D в Telegram\n\n"
        "Команды:\n"
        "/create — создать персонажа\n"
        "/roll `d20` — бросить кубики\n"
        "/check — проверка характеристики\n"
        "/attack — атака по цели\n"
        "/heal — вылечить\n"
        "/sheet — лист персонажа\n"
        "/npc — поговорить с NPC\n"
        "/delete — удалить персонажа\n\n"
        "Сначала создайте героя: /create",
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
    char = await get_or_warn(message)
    if char:
        await message.answer(format_character(char), parse_mode="HTML")


@dp.message(Command("roll"))
async def cmd_roll(message: Message):
    """Бросок кубиков. Формат: /roll 2d6+3"""
    char = await get_or_warn(message)
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
    """Проверка характеристики. Формат: /check str 15"""
    char = await get_or_warn(message)
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

    if ai.available:
        try:
            narrative = await ai.narrate_check(result)
            text += f"\n\n_{narrative}_"
        except Exception:
            pass

    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("attack"))
async def cmd_attack(message: Message):
    """Атака по NPC. Формат: /attack Гоблин 12 15"""
    char = await get_or_warn(message)
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

    if ai.available:
        try:
            narrative = await ai.narrate_attack(result)
            text += f"\n\n_{narrative}_"
        except Exception:
            pass

    db.save_character(message.from_user.id, char)
    await message.answer(text, parse_mode="Markdown")


@dp.message(Command("heal"))
async def cmd_heal(message: Message):
    """Лечение. Формат: /heal 10 (без аргумента — 1d4)"""
    char = await get_or_warn(message)
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

    if ai.available:
        try:
            reply = await ai.npc_dialogue(npc_name, npc_role, user_msg)
            await message.answer(f"🗣 {npc_name}:\n{reply}")
        except Exception as e:
            await message.answer(f"NPC молчит... (ошибка: {e})")
    else:
        await message.answer(
            "💬 AI недоступен. Укажите GROQ_API_KEY в .env для диалогов."
        )


# ─── Быстрые кнопки ───────────────────────────────────────

@dp.message(F.text == "🎲 Бросок")
async def quick_roll(message: Message):
    char = await get_or_warn(message)
    if not char:
        return
    result = Dice.d20(mod=0)
    await message.answer(
        f"🎲 d20: {result['natural']} = **{result['total']}**",
        parse_mode="Markdown",
    )


@dp.message(F.text == "📋 Лист")
async def quick_sheet(message: Message):
    char = await get_or_warn(message)
    if char:
        await message.answer(format_character(char), parse_mode="HTML")


@dp.message(F.text == "⚔️ Атака")
async def quick_attack(message: Message):
    char = await get_or_warn(message)
    if not char:
        return
    # Демо-атака по гоблину
    goblin = Character(name="Гоблин", ac=12, max_hp=7, current_hp=7,
                       dex=14, weapon="1d6", weapon_mod="dex")
    result = attack(char, goblin)
    text = format_attack(result)
    db.save_character(message.from_user.id, char)
    await message.answer(text, parse_mode="Markdown")


@dp.message(F.text == "✨ Проверка")
async def quick_check(message: Message):
    char = await get_or_warn(message)
    if not char:
        return
    await message.answer(
        "Выберите характеристику (DC = 10):",
        reply_markup=stat_select_kb(10),
    )


@dp.callback_query(F.data.startswith("stat:"))
async def cb_stat_check(callback: CallbackQuery):
    """Обработка выбора характеристики для быстрой проверки."""
    parts = callback.data.split(":")
    stat = parts[2]
    dc = int(parts[3]) if len(parts) > 3 else 10
    char = db.get_character(callback.from_user.id)
    if not char:
        await callback.answer("Сначала создайте: /create")
        return
    result = action_check(char, stat, dc)
    text = format_check(result)
    if ai.available:
        try:
            narrative = await ai.narrate_check(result)
            text += f"\n\n_{narrative}_"
        except Exception:
            pass
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


@dp.message(F.text == "💊 Лечить")
async def quick_heal(message: Message):
    char = await get_or_warn(message)
    if not char:
        return
    amount = Dice.roll("1d4")["total"]
    new_hp = char.heal(amount)
    db.save_character(message.from_user.id, char)
    await message.answer(
        f"💊 {char.name} выпивает зелье. Восстановлено {amount} HP. "
        f"Текущее HP: {new_hp}/{char.max_hp}"
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
      
