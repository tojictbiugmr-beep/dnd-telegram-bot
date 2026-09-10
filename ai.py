"""
Groq AI — нарративный движок с Dual-Mode Narrative Director.
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

    async def narrate_action(self, player_action: str, director=None) -> str:
        """
        Главный метод — нарративное описание любого действия игрока.
        Использует director.build_system_prompt() если director передан.
        """
        if not self.available:
            return ""

        system_prompt = director.build_system_prompt() if director else (
            "Ты — мастер D&D. Описывай действия в стиле фэнтези. "
            "2-4 предложения. Без эмодзи."
        )

        ctx_str = ""
        if director:
            ctx = director.get_context()
            ctx_str = (
                f"\n\nКонтекст: Milestone='{ctx['current_milestone']}' "
                f"(прогресс {ctx['milestone_progress']}%), "
                f"напряжение={ctx['tension']}/100, "
                f"режим={ctx['mode']}"
            )

        user_msg = f"Действие игрока: {player_action}{ctx_str}"
        return await self._chat(system=system_prompt, user=user_msg, max_tokens=200)

    async def narrate_check(self, result: dict, director=None) -> str:
        """Нарративное описание результата проверки d20."""
        if not self.available:
            return ""

        stat_name = result.get("stat_name", "действие")
        roll = result["roll"]
        total = result["total"]
        dc = result["dc"]
        crit = result.get("crit")
        success = result["success"]

        mode_info = ""
        if director:
            ctx = director.get_context()
            mode_info = (
                f"\n\nРежим: {ctx['mode'].upper()}, "
                f"напряжение: {ctx['tension']}/100"
            )

        if crit == "success":
            user_msg = (
                f"Критический успех! Проверка {stat_name}: "
                f"d20={roll}, итог={total}, DC={dc}.{mode_info}"
            )
        elif crit == "fail":
            user_msg = (
                f"Критический провал! Проверка {stat_name}: "
                f"d20={roll}, итог={total}, DC={dc}.{mode_info}"
            )
        elif success:
            user_msg = (
                f"Успех. Проверка {stat_name}: "
                f"d20={roll}, итог={total}, DC={dc}.{mode_info}"
            )
        else:
            user_msg = (
                f"Провал. Проверка {stat_name}: "
                f"d20={roll}, итог={total}, DC={dc}.{mode_info}"
            )

        system_prompt = director.build_system_prompt() if director else (
            "Ты — мастер D&D. Описывай действия коротко, ярко. "
            "1-2 предложения. Без эмодзи."
        )
        return await self._chat(system=system_prompt, user=user_msg, max_tokens=100)

    async def narrate_attack(self, result: dict, director=None) -> str:
        """Нарративное описание результата атаки."""
        if not self.available:
            return ""

        attacker = result["attacker"]
        target = result["target"]
        hit = result["hit"]
        crit = result.get("crit")
        damage = result.get("damage", 0)

        mode_info = ""
        if director:
            ctx = director.get_context()
            mode_info = (
                f"\n\nРежим: {ctx['mode'].upper()}, "
                f"напряжение: {ctx['tension']}/100"
            )

        if not hit:
            user_msg = f"{attacker} атакует {target}, но промахивается.{mode_info}"
        elif crit:
            user_msg = (
                f"{attacker} критически попадает по {target} "
                f"— {damage} урона.{mode_info}"
            )
        else:
            user_msg = (
                f"{attacker} попадает по {target} "
                f"— {damage} урона.{mode_info}"
            )

        system_prompt = director.build_system_prompt() if director else (
            "Ты — мастер D&D. Описывай бой коротко, динамично. "
            "1-2 предложения. Без эмодзи."
        )
        return await self._chat(system=system_prompt, user=user_msg, max_tokens=100)

    async def npc_dialogue(self, npc_name: str, npc_role: str,
                           user_message: str, director=None) -> str:
        """Диалог с NPC в характере роли, с учётом контекста мира."""
        if not self.available:
            return "(AI недоступен — укажите GROQ_API_KEY)"

        system = (
            f"Ты — {npc_name}, {npc_role} в мире D&D. "
            f"Отвечай в характере роли. Коротко, живо, 2-3 предложения. "
            f"Без эмодзи. Говори от первого лица."
        )
        if director:
            ctx = director.get_context()
            system += (
                f"\n\nКонтекст мира: {ctx['mode'].upper()} режим. "
                f"Текущая цель: {ctx['current_milestone']}. "
                f"Напряжение: {ctx['tension']}/100."
            )
            if ctx["mode"] == "plot":
                system += (
                    " NPC может намекнуть на сюжетную цель, "
                    "если это уместно."
                )

        return await self._chat(system=system, user=user_message, max_tokens=200)

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
