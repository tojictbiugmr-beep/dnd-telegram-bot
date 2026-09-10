"""
Игровой движок: персонажи, кубики, проверки характеристик, атаки.
"""

import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class Dice:
    @staticmethod
    def roll(spec: str) -> Dict[str, Any]:
        """
        Разбор строки вида: d20, 2d6, 2d6+3, 2d6-1
        Возвращает: {"rolls": [1,2,3], "mod": 3, "total": 6}
        """
        spec = spec.lower().replace(" ", "")
        mod = 0

        # Извлекаем модификатор (+3, -1)
        if "+" in spec:
            parts = spec.split("+")
            mod_str = parts[-1]
            spec = "+".join(parts[:-1])
            mod = int(mod_str)
        elif "-" in spec and spec.count("-") == 1 and spec[0] != "-":
            # чтобы не путать с отрицательным первым числом
            idx = spec.rfind("-")
            if idx > 0 and spec[idx-1].isdigit():
                mod_str = spec[idx:]
                spec = spec[:idx]
                mod = int(mod_str)

        # Теперь разбираем XdY
        if spec == "d20":
            count, sides = 1, 20
        elif "d" in spec:
            c_s = spec.split("d")
            count = int(c_s[0]) if c_s[0] else 1
            sides = int(c_s[1])
        else:
            # Если просто число — считаем как 1dN
            count, sides = 1, int(spec)

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + mod
        return {"rolls": rolls, "mod": mod, "total": total}

    @staticmethod
    def d20(mod: int = 0) -> Dict[str, Any]:
        r = random.randint(1, 20)
        return {"natural": r, "mod": mod, "total": r + mod}


STATS = ["str", "dex", "con", "int", "wis", "cha"]
STAT_NAMES = {
    "str": "Сила",
    "dex": "Ловкость",
    "con": "Телосложение",
    "int": "Интеллект",
    "wis": "Мудрость",
    "cha": "Харизма",
}

@dataclass
class Character:
    name: str
    class_key: str = "fighter"
    level: int = 1
    max_hp: int = field(default=10)
    current_hp: int = field(default=10)
    ac: int = field(default=14)
    stats: Dict[str, int] = field(default_factory=lambda: {"str": 10, "dex": 12, "con": 10, "int": 10, "wis": 10, "cha": 10})
    proficiency: int = field(default=2)
    weapon: str = field(default="1d6")
    weapon_mod: str = field(default="str")  # stat key

    @classmethod
    def quick_create(cls, name: str, class_key: str, level: int):
        base_hp = 10 + (level - 1) * 5
        stats = {
            "str": 14, "dex": 14, "con": 14, "int": 10, "wis": 10, "cha": 10
        }
        ac = 16 if class_key == "rogue" else 18
        if class_key == "wizard":
            ac = 14
        return cls(
            name=name,
            class_key=class_key,
            level=level,
            max_hp=base_hp,
            current_hp=base_hp,
            ac=ac,
            stats=stats,
            proficiency=2 + (level // 4),
        )

    def stat_mod(self, stat: str) -> int:
        val = self.stats.get(stat, 10)
        return (val - 10) // 2

    def check_stat(self, stat: str, dc: int) -> Dict[str, Any]:
        roll = Dice.d20(self.stat_mod(stat) + self.proficiency)
        success = roll["total"] >= dc
        crit = None
        if roll["natural"] == 20:
            crit = "success"
        elif roll["natural"] == 1:
            crit = "fail"
        return {
            "stat_name": STAT_NAMES.get(stat, stat),
            "roll": roll["natural"],
            "mod": self.stat_mod(stat) + self.proficiency,
            "total": roll["total"],
            "dc": dc,
            "success": success,
            "crit": crit,
        }

    def heal(self, amount: int) -> int:
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp

    def damage(self, amount: int) -> int:
        self.current_hp = max(0, self.current_hp - amount)
        return self.current_hp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "class_key": self.class_key,
            "level": self.level,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "ac": self.ac,
            "stats": self.stats,
            "proficiency": self.proficiency,
            "weapon": self.weapon,
            "weapon_mod": self.weapon_mod,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Character":
        return cls(**d)


def action_check(char: Character, stat: str, dc: int) -> Dict[str, Any]:
    return char.check_stat(stat, dc)


def attack(attacker: Character, defender: Character) -> Dict[str, Any]:
    # Атака: d20 + prof + mod(stat) vs AC
    mod = attacker.stat_mod(attacker.weapon_mod) + attacker.proficiency
    roll = Dice.d20(mod)
    hit = roll["total"] >= defender.ac
    crit = None
    if roll["natural"] == 20:
        crit = "hit"
    elif roll["natural"] == 1:
        crit = "miss"

    damage = 0
    if hit or crit == "hit":
        # урон: разбираем строку типа "1d6", "2d8+3"
        dmg_spec = attacker.weapon
        dice_res = Dice.roll(dmg_spec)
        damage = dice_res["total"]
        defender.damage(damage)

    return {
        "attacker": attacker.name,
        "target": defender.name,
        "hit": hit,
        "crit": crit,
        "roll": roll,
        "damage": damage,
        "def_hp_after": defender.current_hp,
    }


def roll_initiative(char: Character) -> int:
    return Dice.d20(char.stat_mod("dex") + char.proficiency)["total"]
      
