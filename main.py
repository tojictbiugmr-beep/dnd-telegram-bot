import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import config # Предполагаем, что у тебя есть config.py с GROQ_API_KEY
from db import init_db, save_director, get_director
from director import GameDirector

# Настройка логов
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.TELEGRAM_TOKEN)
dp = Dispatcher()

# --- FSM ---
class SettingState(StatesGroup):
    waiting_for_setting = State()

# --- Хендлеры ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Добро пожаловать в D&D приключение. Начни с создания мира: /setting")

@dp.message(Command("newgame"))
async def cmd_newgame(message: types.Message, state: FSMContext):
    await state.clear()
    director = get_director(message.chat.id)
    director.setting_description = "" # Сброс мира
    save_director(message.chat.id, director)
    await message.answer("Игра сброшена. Создай новый мир: /setting")

@dp.message(Command("setting"))
async def cmd_setting(message: types.Message, state: FSMContext):
    await state.set_state(SettingState.waiting_for_setting)
    await message.answer("🌍 Опиши свой мир. Например: 'Мрачный лес, где правят духи'.")

@dp.message(SettingState.waiting_for_setting)
async def process_setting(message: types.Message, state: FSMContext):
    description = message.text
    
    # 1. Получаем директора
    director = get_director(message.chat.id)
    
    # 2. Устанавливаем сеттинг
    director.set_setting(description)
    
    # 3. (Здесь можно вызвать AI для генерации квестов, если он доступен)
    # director.add_milestone("Главная цель", "Останови ведьму", 0)
    
    # 4. Сохраняем
    save_director(message.chat.id, director)
    
    # 5. Сбрасываем состояние FSM
    await state.clear()
    
    # 6. Ответ пользователю
    await message.answer(f"🌍 Мир создан!\n\n{description}\n\nТеперь создай персонажа: /create")

@dp.message(F.text)
async def free_text_action(message: types.Message, state: FSMContext):
    # Если мы все еще ждем сеттинг (на случай багов), игнорируем или просим еще раз
    current_state = await state.get_state()
    if current_state == SettingState.waiting_for_setting:
        return # Пусть сработает хендлер выше

    # Получаем директора
    director = get_director(message.chat.id)
    
    # ГЛАВНАЯ ПРОВЕРКА: Если сеттинга нет, просим его, не пытаясь играть
    if not director.has_setting():
        await message.answer("Сначала задай мир: /setting")
        return

    # Если сеттинг есть — это игровой ход
    # Здесь логика взаимодействия с AI и обновлением напряжения
    action = message.text
    director.player_history.append(action)
    
    # Пример заглушки, если AI нет
    response = f"🎲 Ты делаешь: {action}\n"
    response += f"Напряжение мира: {director.tension}/100\n"
    response += f"Текущая цель: {director.get_current_milestone()['name'] if director.get_current_milestone() else 'Нет цели'}"
    
    save_director(message.chat.id, director)
    await message.answer(response)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio
.run(main())
