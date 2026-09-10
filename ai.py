"""
Groq AI через OpenAI SDK.
Генерация нарратива, каркаса истории, диалогов NPC.
Если ключ не задан — все методы возвращают пустую строку.
"""

import logging

log = logging.getLogger("dnd-bot.ai")

SYSTEM_PROMPT = (
    "Ты — Dungeon Master мрачного фэнтези. Веди сюжет к ключевым точкам, "
    "но не лишай игрока свободы. "
    "Каждое случайное событие должно быть связано с глобальным лором. "
    "Пиши атмосферно, на русском, без списков и маркеров. Только живой текст. "
    "ВАЖНО: Если в контексте памяти уже зафиксирован факт (факел горит, герой ранен, "
    "дверь заперта), ты НЕ МОЖЕШЬ его отменить без веской причины в текущем ходе. "
    "Используй факты из памяти и НАВЫКИ героя для поддержания непрерывности мира. "
    "Если игроку был показан результат броска кубика, учитывай его в описании: "
    "успех — действие удалось, неудача — провалилось с последствиями."
)


class GroqAI:
    def __init__(self, api_key: str, model: str = "groq/compound-mini",
                 base_url: str = "https://api.groq.com/openai/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.available = bool(api_key)
        self._client = None

        if self.available:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url,
                )
                log.info("Groq AI инициализирован: model=%s", model)
            except ImportError:
                log.warning("Библиотека openai не установлена. pip install openai")
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
        user = (
            f"Мир: {ctx['setting']}\n"
            f"Текущая цель: {ctx['current_milestone']}\n"
            f"Напряжение: {ctx['tension']}/100\n"
            f"Действие игрока: {action}"
        )
        return await self._chat(SYSTEM_PROMPT, user)

    async def narrate_check(self, result: dict, director) -> str:
        ctx = director.get_context()
        status = "успех" if result["success"] else "провал"
        if result["crit"]:
            status = "критический успех"
        if result["fumble"]:
            status = "критический провал"
        user = (
            f"Проверка: {result['stat_name']}, DC {result['dc']}, "
            f"Бросок: {result['roll']['total']}, {status}.\n"
            f"Мир: {ctx['setting']}"
        )
        return await self._chat(SYSTEM_PROMPT, user)

    async def narrate_attack(self, result: dict, director) -> str:
        ctx = director.get_context()
        if result["hit"]:
            user = (
                f"{result['attacker'].name} атакует {result['target'].name}. "
                f"Попадание! Урон: {result['damage']}. "
                f"HP цели: {result['target_hp']}."
            )
        else:
            user = f"{result['attacker'].name} атакует {result['target'].name}. Промах!"
        user += f"\nМир: {ctx['setting']}"
        return await self._chat(SYSTEM_PROMPT, user)

    async def npc_dialogue(self, name: str, role: str, message: str, director) -> str:
        ctx = director.get_context()
        system = (
            f"Ты — NPC по имени {name}, роль: {role}. "
            f"Отвечай персонажу, оставаясь в роли. 2-3 предложения. На русском."
        )
        user = f"Мир: {ctx['setting']}\nИгрок говорит: {message}"
        return await self._chat(system, user)
