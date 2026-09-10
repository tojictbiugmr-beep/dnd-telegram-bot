"""
Groq AI: генерация нарратива, каркаса истории, диалогов NPC.
Если ключ не задан — все методы возвращают пустую строку.
"""

import logging

log = logging.getLogger("dnd-bot.ai")


class GroqAI:
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.available = bool(api_key)
        self._client = None
        if self.available:
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=api_key)
            except ImportError:
                log.warning("Библиотека groq не установлена. pip install groq")
                self.available = False
            except Exception as e:
                log.warning(f"Не удалось инициализировать Groq: {e}")
                self.available = False

    async def _chat(self, system: str, user: str, max_tokens: int = 1024) -> str:
        if not self._client:
            return ""
        try:
            resp = await self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.8,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            log.error(f"Groq API error: {e}")
            return ""

    async def generate_framework(self, setting: str) -> str:
        system = (
            "Ты — игровой мастер D&D. Создай каркас истории из 3-5 сюжетных целей. "
            "Формат — строго по одной цели на строку, разделён вертикальной чертой:\n"
            "Название | Описание | ключевые,слова,через,запятую\n"
            "Пиши на русском. Без лишнего текста."
        )
        user = f"Сеттинг: {setting}"
        return await self._chat(system, user)

    async def generate_scene(self, action: str, director) -> str:
        ctx = director.get_context()
        system = (
            "Ты — рассказчик в текстовой RPG. Опиши результат действия игрока "
            "в 2-4 предложениях. Атмосферно, но кратко. На русском."
        )
        user = (
            f"Мир: {ctx['setting']}\n"
            f"Текущая цель: {ctx['current_milestone']}\n"
            f"Напряжение: {ctx['tension']}/100\n"
            f"Действие игрока: {action}"
        )
        return await self._chat(system, user)

    async def narrate_check(self, result: dict, director) -> str:
        ctx = director.get_context()
        status = "успех" if result["success"] else "провал"
        if result["crit"]:
            status = "критический успех"
        if result["fumble"]:
            status = "критический провал"
        system = "Ты — рассказчик D&D. Опиши результат проверки в 1-2 предложениях. На русском."
        user = (
            f"Проверка: {result['stat_name']}, DC {result['dc']}, "
            f"Бросок: {result['roll']['total']}, {status}.\n"
            f"Мир: {ctx['setting']}"
        )
        return await self._chat(system, user)

    async def narrate_attack(self, result: dict, director) -> str:
        ctx = director.get_context()
        system = "Ты — рассказчик D&D. Опиши атаку в 1-2 предложениях. На русском."
        if result["hit"]:
            user = (
                f"{result['attacker'].name} атакует {result['target'].name}. "
                f"Попадание! Урон: {result['damage']}. "
                f"HP цели: {result['target_hp']}."
            )
        else:
            user = f"{result['attacker'].name} атакует {result['target'].name}. Промах!"
        user += f"\nМир: {ctx['setting']}"
        return await self._chat(system, user)

    async def npc_dialogue(self, name: str, role: str, message: str, director) -> str:
        ctx = director.get_context()
        system = (
            f"Ты — NPC по имени {name}, роль: {role}. "
            f"Отвечай персонажу, оставаясь в роли. 2-3 предложения. На русском."
        )
        user = f"Мир: {ctx['setting']}\nИгрок говорит: {message}"
        return await self._chat(system, user)
