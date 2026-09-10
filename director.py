import json
from typing import List, Optional, Dict, Any

class GameDirector:
    def __init__(self):
        self.setting_description: str = ""
        self.story_framework: str = ""
        self.milestones: List[Dict[str, Any]] = 
        self.tension: int = 0
        self.current_milestone_idx: int = 0
        self.player_history: List[str] = 

    def set_setting(self, description: str):
        self.setting_description = description.strip()
        self.story_framework = ""  # Очищаем старый каркас при смене мира
        self.milestones = 
        self.tension = 0
        self.current_milestone_idx = 0

    def has_setting(self) -> bool:
        return bool(self.setting_description)

    def add_milestone(self, name: str, description: str, progress: int = 0):
        self.milestones.append({
            "name": name,
            "description": description,
            "progress": progress,
            "completed": False
        })

    def get_current_milestone(self) -> Optional[Dict[str, Any]]:
        if not self.milestones:
            return None
        if self.current_milestone_idx >= len(self.milestones):
            self.current_milestone_idx = len(self.milestones) - 1
        return self.milestones[self.current_milestone_idx]

    def to_dict(self) -> dict:
        # ГЛАВНОЕ: Явно перечисляем все поля, чтобы ничего не потерялось при сохранении
        return {
            "setting_description": self.setting_description,
            "story_framework": self.story_framework,
            "milestones": self.milestones,
            "tension": self.tension,
            "current_milestone_idx": self.current_milestone_idx,
            "player_history": self.player_history
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameDirector":
        director = cls()
        # Используем .get() с дефолтными значениями, чтобы не упасть, если поле отсутствует
        director.setting_description = data.get("setting_description", "")
        director.story_framework = data.get("story_framework", "")
        director.milestones = data.get("milestones", )
        director.tension = data.get("tension", 0)
        director.current_milestone_idx = data.get("current_milestone_idx", 0)
        director.player_history = data.get("player_history", )
        return di
rector
