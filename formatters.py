"""
Форматирование результатов движка в текст для Telegram.
"""

STAT_NAMES = {
    "str": "Сила", "dex": "Ловкость", "con": "Телосложение",
    "int": "Интеллект", "wis": "Мудрость", "cha": "Харизма",
}


def format_mod(mod: int) -> str:
    return f"+{mod}" if mod >= 0 else str(mod)


def format_check(r: dict) -> str:
    """Формат результата проверки характеристики."""
    mod_str = format_mod(r["mod"])
    if r["bonus"]:
        mod_str += f" + {format_mod(r['bonus'])}"
    line = f"🎲 {r['stat_name']} | d20: {r['roll']} ({mod_str}) = {r['total']}\n"
    line += f"   DC {r['dc']} → "
    if r["crit"] == "success":
        line += "✅ КРИТ!"
    elif r["crit"] == "fail":
        line += "❌ Критпровал!"
    elif r["success"]:
        line += "✅ Успех"
    else:
        line += "❌ Провал"
    return line


def format_attack(r: dict) -> str:
    """Формат результата атаки."""
    line = f"⚔️ {r['attacker']} → {r['target']}\n"
    if not r["hit"]:
        return line + "   Промах!"
    tag = " 🎯 КРИТ!" if r["crit"] else ""
    line += f"   Попадание{tag} Урон: {r['damage']} → HP: {r['target_hp_after']}"
    if r["target_hp_after"] == 0:
        line += " 💀"
    return line


def format_character(char) -> str:
    """Формат листа персонажа (HTML для Telegram)."""
    lines = [
        f"📋 <b>{char.name}</b> — Ур.{char.level}",
        f"❤️ HP: {char.current_hp}/{char.max_hp}",
        f"🛡 AC: {char.ac}  |  Мастерство: +{char.proficiency}",
        "",
        "<b>Характеристики:</b>",
    ]
    for s in ["str", "dex", "con", "int", "wis", "cha"]:
        val = getattr(char, s)
        mod = format_mod((val - 10) // 2)
        lines.append(f"  {STAT_NAMES[s]}: {val} ({mod})")
    lines.append(f"\n🗡 Оружие: {char.weapon} ({char.weapon_mod})")
    return "\n".join(lines)
