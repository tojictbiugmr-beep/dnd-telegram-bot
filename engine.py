"""
Игровая механика D&D: персонаж, кубики, проверки, атаки.
Ничего не знает про Telegram — чистая логика.
"""

import random
from dataclasses import dataclass, field

# ─── Характеристики ──────────────────────────────────────

STATS = ["str", "dex", "con", "int", "wis", "cha"]

STAT_NAMES = {
    "str": "Сила",
    "dex": "Ловкость",
    "con": "Телосложение",
    "int": "Интеллект",
    "wis": "Мудрость",
    "cha": "Харизма",
}

CLASS_TEMPLATES = {
    "fighter": {
        "stats": {"str": 16, "dex": 14, "con": 16, "int": 10, "wis": 10, "cha": 10},
        "hp": 12, "ac": 16, "weapon": "1d8", "weapon_mod": "str",
    },
    "rogue": {
        "stats": {"str": 10, "dex": 16, "con": 14, "int": 12, "wis": 14, "cha": 12},
        "hp": 10, "ac": 14, "weapon": "1d6", "weapon_mod": "dex",
    },
    "wizard": {
        "stats": {"str": 8, "dex": 14, "con": 12, "int": 16, "wis": 12, "cha": 10},
        "hp": 8, "ac": 12, "weapon": "1d6", "weapon_mod": "int",
    },
    "cleric": {
        "stats": {"str": 14, "dex": 10, "con": 14, "int": 10, "wis": 16, "cha": 12},
        "hp": 10, "ac": 16, "weapon": "1d6", "weapon_mod": "wis",
    },
}


def stat_mod(score: int) -> int:
    return (score - 10) // 2


# ─── Кубики ──────────────────────────────────────────────

class Dice:
    @staticmethod
    def d20(mod: int = 0) -> dict:
        nat = random.randint(1, 20)
        return {"natural": nat, "total": nat + mod, "mod": mod}

    @staticmethod
    def roll(spec: str) -> dict:
        spec = spec.lower().replace(" ", "")
        mod = 0
        if "+" in spec:
            dice_part, mod_part = spec.split("+", 1)
            mod = int(mod_part)
        elif "-" in spec:
            dice_part, mod_part = spec.split("-", 1)
            mod = -int(mod_part)
        else:
            dice_part = spec

        if "d" in dice_part:
            n, sides = dice_part.split("d", 1)
            n = int(n) if n else 1
            sides = int(sides)
        else:
            n = 1
            sides = int(dice_part)

        rolls = [random.randint(1, sides) for _ in range(n)]
        total = sum(rolls) + mod
        return {"rolls": rolls, "mod": mod, "total": total, "spec": spec}


# ─── Персонаж ─────────────────────────────────────────────

@dataclass
class Character:
    name: str = "Герой"
    class_key: str = "fighter"
    level: int = 1
    max_hp: int = 10
    current_hp: int = 10
    ac: int = 10
    stats: dict = field(default_factory=lambda: {s: 10 for s in STATS})
    weapon: str = "1d6"
    weapon_mod: str = "str"
    xp: int = 0

    @classmethod
    def quick_create(cls, name: str, class_key: str, level: int = 1) -> "Character":
        tmpl = CLASS_TEMPLATES.get(class_key, CLASS_TEMPLATES["fighter"])
        hp = tmpl["hp"] + stat_mod(tmpl["stats"]["con"])
        return cls(
            name=name, class_key=class_key, level=level,
            max_hp=hp, current_hp=hp, ac=tmpl["ac"],
            stats=tmpl["stats"].copy(),
            weapon=tmpl["weapon"], weapon_mod=tmpl["weapon_mod"],
        )

    def get_mod(self, stat: str) -> int:
        return stat_mod(self.stats.get(stat, 10))

    def heal(self, amount: int) -> int:
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        return self.current_hp

    def take_damage(self, amount: int) -> int:
        self.current_hp = max(0, self.current_hp - amount)
        return self.current_hp

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def to_dict(self) -> dict:
        return {
            "name": self.name, "class_key": self.class_key, "level": self.level,
            "max_hp": self.max_hp, "current_hp": self.current_hp, "ac": self.ac,
            "stats": self.stats, "weapon": self.weapon, "weapon_mod": self.weapon_mod,
            "xp": self.xp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        return cls(
            name=data.get("name", "Герой"),
            class_key=data.get("class_key", "fighter"),
            level=data.get("level", 1),
            max_hp=data.get("max_hp", 10),
            current_hp=data.get("current_hp", 10),
            ac=data.get("ac", 10),
            stats=data.get("stats", {s: 10 for s in STATS}),
            weapon=data.get("weapon", "1d6"),
            weapon_mod=data.get("weapon_mod", "str"),
            xp=data.get("xp", 0),
        )


# ─── Механики ─────────────────────────────────────────────

def action_check(char: Character, stat: str, dc: int) -> dict:
    mod = char.get_mod(stat)
    roll = Dice.d20(mod=mod)
    return {
        "stat": stat, "stat_name": STAT_NAMES.get(stat, stat),
        "dc": dc, "roll": roll,
        "success": roll["total"] >= dc,
        "crit": roll["natural"] == 20,
        "fumble": roll["natural"] == 1,
        "character": char,
    }


def attack(attacker: Character, target: Character) -> dict:
    mod = attacker.get_mod(attacker.weapon_mod)
    roll = Dice.d20(mod=mod)
    hit = roll["total"] >= target.ac
    crit = roll["natural"] == 20
    fumble = roll["natural"] == 1
    damage = 0
    if fumble:
        hit = False
    elif hit:
        damage = Dice.roll(attacker.weapon)["total"]
        if crit:
            damage += Dice.roll(attacker.weapon)["total"]
        target.take_damage(damage)
    return {
        "attacker": attacker, "target": target, "roll": roll,
        "hit": hit, "crit": crit, "fumble": fumble,
        "damage": damage, "target_hp": target.current_hp,
        "target_dead": not target.is_alive(),
    }
