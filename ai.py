"""
Groq AI — нарративные описания бросков и диалоги с NPC.
Если ключ не указан, все методы тихо возвращают пустую строку.
"""

import logging

log = logging.getLogger("dnd-bot.ai")


class GroqAI:
    def __init__(self, api_key: str = "", model: str = "llama-3.3-70b-versatile"):
        self.api_key = api_key
        self.model = model
        self.available = bool(api_key)
        self._client = None
        if self.available:
            try:
                from groq import AsyncGroq
                self._client = AsyncGroq(api_key=api_key)
            except ImportError:
                log.warning("groq не установлен. AI-функции отключены.")
                self.available = False

    async def narrate_check(self, result: dict) -> str:
        """Короткое нарративное описание результата проверки d20."""
        if not self.available:
            return ""
        stat_name = result.get("stat_name", "действие")
        roll = result["roll"]
        total = result["total"]
        dc = result["dc"]
        crit = result.get("crit")

        if crit == "success":
            prompt = (
                f"Игрок сделал проверку {stat_name}, бросок d20={roll}, "
                f"итог={total}, DC={dc}. Критический успех! "
                f"Опиши эффект в 1 предложении, эпично."
            )
        elif crit == "fail":
            prompt = (
                f"Игрок сделал проверку {stat_name}, бросок d20={roll}, "
                f"итог={total}, DC={dc}. Критический провал! "
                f"Опиши катастрофу в 1 предложении."
            )
        elif result["success"]:
            prompt = (
                f"Игрок сделал проверку {stat_name}, бросок d20={roll}, "
                f"итог={total}, DC={dc}. Успех. "
                f"Коротко опиши в 1 предложении."
            )
        else:
            prompt = (
                f"Игрок сделал проверку {stat_name}, бросок d20={roll}, "
                f"итог={total}, DC={dc}. Провал. "
                f"Коротко опиши в 1 предложении."
            )

        return await self._chat(
            system="Ты — мастер D&D. Описывай действия коротко, ярко, в стиле фэнтези. 1-2 предложения максимум. Без эмодзи.",
            user=prompt,
            max_tokens=100,
        )

    async def narrate_attack(self, result: dict) -> str:
        """Короткое нарративное описание результата атаки."""
        if not self.available:
            return ""
        attacker = result["attacker"]
        target = result["target"]
        hit = result["hit"]
        crit = result.get("crit")
        damage = result.get("damage", 0)

        if not hit:
            prompt = f"{attacker} атакует {target}, но промахивается. Опиши в 1 предложении."
        elif crit:
            prompt = (
                f"{attacker} критически попадает по {target} и наносит {damage} урона. "
                f"Опиши эффектно в 1 предложении."
            )
        else:
            prompt = (
                f"{attacker} попадает по {target} и наносит {damage} урона. "
                f"Опиши в 1 предложении."
            )

        return await self._chat(
            system="Ты — мастер D&D. Описывай бой коротко, динамично, в стиле фэнтези. 1-2 предложения максимум. Без эмодзи.",
            user=prompt,
            max_tokens=100,
        )

    async def npc_dialogue(self, npc_name: str, npc_role: str, user_message: str) -> str:
        """Ответ NPC в диалоге с игроком."""
        if not self.available:
            return "(AI недоступен — укажите GROQ_API_KEY)"
        system = (
            f"Ты — {npc_name}, {npc_role} в мире D&D. "
            f"Отвечай в характере роли. Коротко, живо, 2-3 предложения. "
            f"Без эмодзи. Говори от первого лица."
        )
        return await self._chat(
            system=system,
            user=user_message,
            max_tokens=200,
        )

    async def _chat(self, system: str, user: str, max_tokens: int = 150) -> str:
        """Низкоуровневый вызов Groq."""
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
            return f"(ошибка: {e})"
          
