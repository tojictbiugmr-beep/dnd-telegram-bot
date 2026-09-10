"""
Dual-Mode Narrative Director — управление сюжетом и сеттингом.
"""


class GameDirector:
    """
    Управление сюжетным состоянием: milestones, tension, режимы, сеттинг.
    """

    PRESET_SETTINGS = {
        "dark_fantasy": {
            "name": "Тёмное фэнтези",
            "description": (
                "Мрачный мир упадка, где цивилизация рушится. "
                "Древние культы пробуждаются, тьма наступает с окраин. "
                "Магия опасна и непредсказуема."
            ),
            "tone": "мрачный, готический",
            "themes": "упадок, коррупция, древнее зло",
        },
        "high_fantasy": {
            "name": "Высокое фэнтези",
            "description": (
                "Классический мир магии и героев. Эльфийские леса, "
                "гномьи города, королевства людей. "
                "Драконы и великаны — часть мира."
            ),
            "tone": "эпический, героический",
            "themes": "добро vs зло, честь, приключения",
        },
        "post_apoc": {
            "name": "Постапокалипсис",
            "description": (
                "Мир после катастрофы. Руины древних городов, "
                "мутанты, остатки технологий. Выживание — главная цель."
            ),
            "tone": "суровый, безнадёжный",
            "themes": "выживание, потеря, надежда",
        },
        "steampunk": {
            "name": "Стимпанк",
            "description": (
                "Мир пара и шестерёнок. Воздушные корабли, "
                "механические создания, алхимия. "
                "Империи борются за ресурсы."
            ),
            "tone": "индустриальный, авантюрный",
            "themes": "прогресс vs природа, изобретения, интриги",
        },
        "horror": {
            "name": "Хоррор",
            "description": (
                "Готический мир страха. Проклятые поместья, "
                "нежить, тёмные ритуалы. Рассвет — редкая удача."
            ),
            "tone": "напряжённый, пугающий",
            "themes": "страх, безумие, неизвестность",
        },
    }

    def __init__(self):
        self.milestones: list = []
        self.current_milestone_idx: int = 0
        self.tension: int = 0
        self.tension_threshold: int = 50
        self.player_history: list = []
        self.milestone_proximity: int = 0
        self.proximity_threshold: int = 30
        self.setting_key: str = ""
        self.setting_custom: str = ""

    # ─── Сеттинг ──────────────────────────────────────────

    def set_setting(self, key: str = "", custom: str = "") -> bool:
        """Установить пресет или кастомный сеттинг."""
        if key in self.PRESET_SETTINGS:
            self.setting_key = key
            self.setting_custom = ""
            return True
        elif custom:
            self.setting_key = "custom"
            self.setting_custom = custom
            return True
        return False

    def get_setting_info(self) -> dict:
        """Информация о текущем сеттинге."""
        if self.setting_key == "custom":
            return {
                "name": "Свой сеттинг",
                "description": self.setting_custom,
                "tone": "свободный",
                "themes": "задаёт игрок",
            }
        elif self.setting_key in self.PRESET_SETTINGS:
            s = self.PRESET_SETTINGS[self.setting_key]
            return {
                "name": s["name"],
                "description": s["description"],
                "tone": s["tone"],
                "themes": s["themes"],
            }
        return {"name": "Не задан", "description": "", "tone": "", "themes": ""}

    def has_setting(self) -> bool:
        return bool(self.setting_key)

    @property
    def setting_list(self) -> list:
        """Список пресетов для кнопок: [(key, label), ...]."""
        return [(k, v["name"]) for k, v in self.PRESET_SETTINGS.items()]

    # ─── Milestones ───────────────────────────────────────

    def add_milestone(self, name: str, description: str, target_actions: list = None):
        self.milestones.append({
            "name": name,
            "description": description,
            "target_actions": target_actions or [],
            "completed": False,
            "progress": 0,
        })

    @property
    def current_milestone(self):
        if self.current_milestone_idx < len(self.milestones):
            return self.milestones[self.current_milestone_idx]
        return None

    @property
    def active_mode(self) -> str:
        if self.tension >= self.tension_threshold:
            return "plot"
        if self.milestone_proximity >= self.proximity_threshold:
            return "plot"
        return "ambient"

    # ─── Анализ ────────────────────────────────────────────

    def analyze_intent(self, player_action: str) -> str:
        action_lower = player_action.lower()
        intents = [
            ("combat", ["атак", "бей", "удар", "руб", "стрел", "заклинан", "убить"]),
            ("social", ["говор", "спрос", "торг", "убежд", "угроз", "обман", "покупать", "рынок"]),
            ("explore", ["идти", "пойти", "осмотр", "исслед", "поиск", "откр", "путешеств"]),
            ("quest", ["квест", "мисси", "цель", "спасти", "артефакт", "найти", "найд"]),
            ("rest", ["отдых", "спать", "выпить", "поесть", "таверн"]),
        ]
        for intent, keywords in intents:
            if any(kw in action_lower for kw in keywords):
                return intent
        return "unknown"

    def is_plot_relevant(self, player_action: str) -> bool:
        ms = self.current_milestone
        if not ms:
            return False
        action_lower = player_action.lower()
        if any(ta.lower() in action_lower for ta in ms["target_actions"]):
            return True
        ms_words = [w for w in ms["name"].lower().split() if len(w) > 3]
        if any(w in action_lower for w in ms_words):
            return True
        return False

    def update_state(self, player_action: str, check_result: dict = None) -> dict:
        intent = self.analyze_intent(player_action)
        plot_relevant = self.is_plot_relevant(player_action)

        if plot_relevant:
            self.milestone_proximity = min(100, self.milestone_proximity + 20)
            self.tension = min(100, self.tension + 15)
        else:
            self.milestone_proximity = max(0, self.milestone_proximity - 5)
            if self.player_history and all(
                not self.is_plot_relevant(h["action"]) for h in self.player_history[-3:]
            ):
                self.tension = min(100, self.tension + 5)

        if check_result and check_result.get("success"):
            if plot_relevant and self.current_milestone:
                self.current_milestone["progress"] = min(
                    100, self.current_milestone["progress"] + 25
                )
                if self.current_milestone["progress"] >= 100:
                    self.current_milestone["completed"] = True
                    self.current_milestone_idx += 1
                    self.milestone_proximity = 0
                    self.tension = max(0, self.tension - 30)

        self.player_history.append({
            "action": player_action,
            "intent": intent,
            "plot_relevant": plot_relevant,
            "mode": self.active_mode,
        })
        return {
            "intent": intent,
            "plot_relevant": plot_relevant,
            "mode": self.active_mode,
            "tension": self.tension,
            "proximity": self.milestone_proximity,
        }

    def get_context(self) -> dict:
        ms = self.current_milestone
        s = self.get_setting_info()
        return {
            "current_milestone": ms["name"] if ms else "Нет активной цели",
            "milestone_progress": ms["progress"] if ms else 0,
            "milestone_description": ms["description"] if ms else "",
            "tension": self.tension,
            "mode": self.active_mode,
            "proximity": self.milestone_proximity,
            "setting": s["name"],
            "setting_description": s["description"],
            "setting_tone": s["tone"],
            "setting_themes": s["themes"],
        }

    def build_system_prompt(self) -> str:
        """Собирает system prompt с сеттингом и режимом."""
        ctx = self.get_context()
        mode = ctx["mode"]

        base = (
            "Ты — Игровой Режиссёр (Game Director) в системе динамического повествования D&D. "
            "Твоя задача — управлять балансом между свободой действий игрока "
            "и движением к ключевым точкам сюжета.\n\n"
            "ИЕРАРХИЯ ПРИОРИТЕТОВ:\n"
            "Global Milestones > Character Arc > Player Agency > Ambient Details\n\n"
            'ПРИНЦИП "Да, но..." / "Нет, и...":\n'
            '• Если игрок делает что-то полезное для сюжета: "Да, это произошло, '
            'И К ТОМУ ЖЕ [сюжетное событие]"\n'
            '• Если игрок делает что-то деструктивное: "Нет, это не сработало, '
            'И ВМЕСТО ЭТОГО [препятствие]"\n\n'
            "ANTI-DRIFT: Каждое событие должно иметь потенциальную связь "
            "с глобальным Лором.\n\n"
        )

        # Блок сеттинга
        if ctx["setting"] != "Не задан":
            base += (
                f"СЕТТИНГ: {ctx['setting']}\n"
                f"Описание мира: {ctx['setting_description']}\n"
                f"Тон: {ctx['setting_tone']}\n"
                f"Темы: {ctx['setting_themes']}\n\n"
            )

        if mode == "ambient":
            base += (
                "РЕЖИМ: AMBIENT (Режим Мира)\n"
                "Мир живёт сам по себе. Не навязывай сюжет. "
                "Будь детальным, но ненавязчивым. "
                "Генерируй детали окружения, реакцию NPC, погоду, "
                "мелкие случайные события.\n"
            )
        else:
            base += (
                "РЕЖИМ: PLOT (Режим Сюжета)\n"
                "Направляй игрока к ключевой точке. Используй:\n"
                "• Narrative Echo: интегрируй сюжет в отклонения игрока\n"
                "• Friction: если игрок сопротивляется сюжету — "
                "увеличивай препятствия\n"
                "• Milestone Injection: активируй события "
                "при достижении условий\n"
            )

        base += (
            f"\nТЕКУЩЕЕ СОСТОЯНИЕ:\n"
            f"• Current Milestone: {ctx['current_milestone']} "
            f"(прогресс: {ctx['milestone_progress']}%)\n"
            f"• Описание цели: {ctx['milestone_description']}\n"
            f"• Сюжетное напряжение: {ctx['tension']}/100\n"
            f"• Активный режим: {mode.upper()}\n"
            f"• Близость к milestone: {ctx['proximity']}%\n"
            f"• Сеттинг: {ctx['setting']}\n\n"
            "Отвечай на русском. 2-4 предложения. Без эмодзи. "
            "В стиле фэнтези (или в соответствии с сеттингом)."
        )
        return base

    # ─── Сериализация ─────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "milestones": self.milestones,
            "current_milestone_idx": self.current_milestone_idx,
            "tension": self.tension,
            "milestone_proximity": self.milestone_proximity,
            "player_history": self.player_history[-20:],
            "setting_key": self.setting_key,
            "setting_custom": self.setting_custom,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameDirector":
        obj = cls()
        obj.milestones = d.get("milestones", [])
        obj.current_milestone_idx = d.get("current_milestone_idx", 0)
        obj.tension = d.get("tension", 0)
        obj.milestone_proximity = d.get("milestone_proximity", 0)
        obj.player_history = d.get("player_history", [])
        obj.setting_key = d.get("setting_key", "")
        obj.setting_custom = d.get("setting_custom", "")
        return obj
        
