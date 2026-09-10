"""
Groq AI — нарративный движок с Dual-Mode Narrative Director.
"""

import logging

log = logging.getLogger("dnd-bot.ai")


class GroqAI:
    def __init__(self, api_key: str = "", model: str = "compound-mini"):
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

    async def generate_framework(self, setting_description: str) -> str:
        if not self.available:
            return ""
        system = (
            "Ты — сценарист D&D-кампаний. По описанию сеттинга создай каркас истории "
            "с 3-5 ключевыми точками (milestones) для игрока.\n\n"
            "Формат — строго по одной точке на строку, разделитель '|':\n"
            "Название | Описание | ключевое_действие1,действие2\n\n"
            "Пример:\n"
            "Прибытие в деревню | Игрок добирается до заброшенной деревни, где начались странности | прибыть деревня\n"
            "Расследование | Нужно узнать причину исчезновения жителей | расследовать искать след\n"
            "Финальная битва | Бой с источником зла в подземелье | атаковать битва подземелье\n\n"
            "Каждое описание — 1-2 предложения. Кратко. Без эмодзи. Без нумерации."
        )
        user = f"Сеттинг:\n{setting_description}\n\nСоздай каркас истории."
        return await self._chat(system=system, user=user, max_tokens=500)

        user = f"Сеттинг:\n{setting_description}\n\nСоздай каркас истории."
        return await self._chat(system=system, user=user, max_tokens=400)

    async def generate_scene(self, player_action: str, director=None) -> str:
        if not self.available:
            return ""
        system_prompt = director.build_system_prompt() if director else (
            "Ты — мастер D&D. Опиши сцену ярко и кратко. 2-4 предложения. Без эмодзи."
        )
        ctx_str = ""
        if director:
            ctx = director.get_context()
            ctx_str = (
                f"\n\nКонтекст: Milestone='{ctx['current_milestone']}' "
                f"({ctx['milestone_progress']}%), "
                f"напряжение={ctx['tension']}/100, "
                f"режим={ctx['mode']}"
            )
            if ctx["framework"]:
                ctx_str += f"\nКаркас: {ctx['framework']}"
        user_msg = f"Действие игрока: {player_action}{ctx_str}"
        return await self._chat(system=system_prompt, user=user_msg, max_tokens=250)

    async def narrate_check(self, result: dict, director=None) -> str:
        if not self.available:
            return ""
        stat_name = result.get("stat_name", "действие")
        roll = result["roll"]
        total = result["total"]
        dc = result["dc"]
        crit = result.get("crit")
        success = result["success"]
        if crit == "success":
            user_msg = f"Критический успех! {stat_name}: d20={roll}, итог={total}, DC={dc}."
        elif crit == "fail":
            user_msg = f"Критический провал! {stat_name}: d20={roll}, итог={total}, DC={dc}."
        elif success:
            user_msg = f"Успех. {stat_name}: d20={roll}, итог={total}, DC={dc}."
        else:
            user_msg = f"Провал. {stat_name}: d20={roll}, итог={total}, DC={dc}."
        if director:
            ctx = director.get_context()
            user_msg += f"\nРежим: {ctx['mode'].upper()}, напряжение: {ctx['tension']}/100"
        system_prompt = director.build_system_prompt() if director else (
            "Ты — мастер D&D. Описывай действия коротко, ярко. 1-2 предложения. Без эмодзи."
        )
        return await self._chat(system=system_prompt, user=user_msg, max_tokens=100)

    async def narrate_attack(self, result: dict, director=None) -> str:
        if not self.available:
            return ""
        attacker = result["attacker"]
        target = result["target"]
        hit = result["hit"]
        crit = result.get("crit")
        damage = result.get("damage", 0)
        if not hit and crit != "hit":
            user_msg = f"{attacker} атакует {target}, но промахивается."
        elif crit == "hit":
            user_msg = f"{attacker} критически попадает по {target} — {damage} урона."
        else:
            user_msg = f"{attacker} попадает по {target} — {damage} урона."
        if director:
            ctx = director.get_context()
            user_msg += f"\nРежим: {ctx['mode'].upper()}, напряжение: {ctx['tension']}/100"
        system_prompt = director.build_system_prompt() if director else (
            "Ты — мастер D&D. Описывай бой динамично. 1-2 предложения. Без эмодзи."
        )
        return await self._chat(system=system_prompt, user=user_msg, max_tokens=100)

    async def npc_dialogue(self, npc_name: str, npc_role: str,
                           user_message: str, director=None) -> str:
        if not self.available:
            return "(AI недоступен — укажите GROQ_API_KEY)"
        system = (
            f"Ты — {npc_name}, {npc_role} в мире D&D. "
            f"Отвечай в характере роли. Коротко, живо, 2-3 предложения. "
            f"Без эмодзи. Говори от первого лица."
        )
        if director:
            ctx = director.get_context()
            system += f"\n\nСеттинг: {ctx['setting']}"
            if ctx["framework"]:
                system += f"\nКаркас: {ctx['framework']}"
            system += f"\nРежим: {ctx['mode'].upper()}, напряжение: {ctx['tension']}/100"
            if ctx["mode"] == "plot":
                system += " NPC может намекнуть на сюжетную цель, если уместно."
        return await self._chat(system=system, user=user_message, max_tokens=200)

    async def _chat(self, system: str, user: str, max_tokens: int = 150) -> str:
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
