"""
Режиссёр сюжета: хранит состояние мира, квесты, напряжение.
Ничего не знает про Telegram.
"""

from typing import Optional


class GameDirector:
    def __init__(self):
        self.setting_description: str = ""
        self.story_framework: str = ""
        self.milestones: list = []
        self.current_milestone_idx: int = 0
        self.tension: int = 0
        self.milestone_proximity: int = 0
        self.player_history: list = []
        self.mode: str = "free"

    # ─── Сеттинг ───────────────────────────────────────────

    def set_setting(self, description: str):
        self.setting_description = description.strip()

    def has_setting(self) -> bool:
        return bool(self.setting_description)

    def get_setting_info(self) -> dict:
        return {"description": self.setting_description, "framework": self.story_framework}

    def set_framework(self, framework: str):
        self.story_framework = framework.strip()

    # ─── Квесты ─────────────────────────────────────────────

    def add_milestone(self, name: str, description: str, target_actions: list = None):
        self.milestones.append({
            "name": name, "description": description,
            "target_actions": target_actions or [],
            "progress": 0, "completed": False,
        })

    def get_current_milestone(self) -> Optional[dict]:
        if not self.milestones:
            return None
        if self.current_milestone_idx >= len(self.milestones):
            self.current_milestone_idx = len(self.milestones) - 1
        if self.current_milestone_idx < 0:
            self.current_milestone_idx = 0
        return self.milestones[self.current_milestone_idx]

    # ─── Состояние ────────────────────────────────────────

    def update_state(self, action: str, result: dict = None) -> dict:
        action_lower = action.lower()
        self.player_history.append(action)
        if len(self.player_history) > 20:
            self.player_history = self.player_history[-20:]

        milestone = self.get_current_milestone()
        if milestone and not milestone["completed"]:
            for kw in milestone.get("target_actions", []):
                if kw.lower() in action_lower:
                    milestone["progress"] = min(100, milestone["progress"] + 25)
                    break
            if result and result.get("success"):
                milestone["progress"] = min(100, milestone["progress"] + 10)
            if milestone["progress"] >= 100:
                milestone["completed"] = True
                self.current_milestone_idx += 1

        self.mode = "plot" if self.milestones else "free"

        if result and result.get("success"):
            self.tension = max(0, self.tension - 5)
        elif result and result.get("fumble"):
            self.tension = min(100, self.tension + 15)
        else:
            self.tension = min(100, self.tension + 2)

        self.milestone_proximity = milestone["progress"] if milestone else 0

        return {
            "mode": self.mode, "tension": self.tension,
            "proximity": self.milestone_proximity,
            "current_milestone": milestone["name"] if milestone else "Нет активной цели",
            "milestone_progress": milestone["progress"] if milestone else 0,
            "milestone_completed": milestone["completed"] if milestone else False,
        }

    def get_context(self) -> dict:
        milestone = self.get_current_milestone()
        return {
            "setting": self.setting_description,
            "framework": self.story_framework,
            "mode": self.mode, "tension": self.tension,
            "proximity": self.milestone_proximity,
            "current_milestone": milestone["name"] if milestone else "Нет активной цели",
            "milestone_progress": milestone["progress"] if milestone else 0,
        }

    # ─── Сериализация ──────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "setting_description": self.setting_description,
            "story_framework": self.story_framework,
            "milestones": self.milestones,
            "current_milestone_idx": self.current_milestone_idx,
            "tension": self.tension,
            "milestone_proximity": self.milestone_proximity,
            "player_history": self.player_history,
            "mode": self.mode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameDirector":
        d = cls()
        d.setting_description = data.get("setting_description", "")
        d.story_framework = data.get("story_framework", "")
        d.milestones = data.get("milestones", [])
        d.current_milestone_idx = data.get("current_milestone_idx", 0)
        d.tension = data.get("tension", 0)
        d.milestone_proximity = data.get("milestone_proximity", 0)
        d.player_history = data.get("player_history", [])
        d.mode = data.get("mode", "free")
        return d
