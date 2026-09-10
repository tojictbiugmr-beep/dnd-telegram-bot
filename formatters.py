"""
Форматирование сообщений для Telegram.
"""

from engine import STATS, STAT_NAMES


def format_character(char) -> str:
    lines = [
        f"<b>{char.name}</b> ({char.class_key}, {char.level} ур.)",
        f"❤️ HP: {char.current_hp}/{char.max_hp}",
        f"🛡 AC: {char.ac}",
    ]
    stat_parts = []
    for s in STATS:
        val = char.stats.get(s, 10)
        mod = (val - 10) // 2
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        stat_parts.append(f"{STAT_NAMES[s]} {val} ({mod_str})")
    lines.append("📊 " + ", ".join(stat_parts))
    lines.append(f"🗡 Оружие: {char.weapon}")
    return "\n".join(lines)


def format_check(result: dict) -> str:
    status = "✅ Успех" if result["success"] else "❌ Провал"
    crit_str = ""
    if result["crit"] == "success":
        crit_str = " 🎯 КРИТ!"
    elif result["crit"] == "fail":
        crit_str = " 💥 Критпровал!"

    mod = result["mod"]
    mod_str = f"+{mod}" if mod >= 0 else str(mod)

    return (
        f"🎲 {result['stat_name']} | d20: {result['roll']} ({mod_str}) = {result['total']}\n"
        f"   DC {result['dc']} → {status}{crit_str}"
    )


def format_attack(result: dict) -> str:
    attacker = result["attacker"]
    target = result["target"]
    line = f"⚔️ {attacker} → {target}\n"

    if not result["hit"] and result["crit"] != "hit":
        return line + "   Промах!"

    tag = " 🎯 КРИТ!" if result["crit"] == "hit" else ""
    line += f"   Попадание{tag} Урон: {result['damage']}"
    line += f" → HP: {result['def_hp_after']}"
    if result["def_hp_after"] == 0:
        line += " 💀"
    
    return line
