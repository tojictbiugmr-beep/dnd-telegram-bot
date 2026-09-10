"""
Форматирование текста для вывода в Telegram.
"""

from engine import STAT_NAMES


def format_character(char) -> str:
    stats_str = ", ".join(
        f"{STAT_NAMES[s]} {char.stats.get(s, 10)}"
        f" ({'+' if char.get_mod(s) >= 0 else ''}{char.get_mod(s)})"
        for s in ["str", "dex", "con", "int", "wis", "cha"]
    )
    return (
        f"<b>{char.name}</b> ({char.class_key}, {char.level} ур.)\n"
        f"❤️ HP: {char.current_hp}/{char.max_hp}\n"
        f"🛡 AC: {char.ac}\n"
        f"📊 {stats_str}\n"
        f"🗡 Оружие: {char.weapon}"
    )


def format_check(result: dict) -> str:
    r = result["roll"]
    status = "✅ Успех" if result["success"] else "❌ Провал"
    if result["crit"]:
        status = "🌟 КРИТ! " + status
    elif result["fumble"]:
        status = "💀 КРИТИЧЕСКИЙ ПРОВАЛ! " + status
    mod_str = f" {'+' + str(r['mod']) if r['mod'] >= 0 else str(r['mod'])}" if r["mod"] else ""
    return (
        f"🎲 Проверка: {result['stat_name']} (DC {result['dc']})\n"
        f"Бросок: d20{mod_str} = {r['natural']}{mod_str} = {r['total']}\n"
        f"Результат: {status}"
    )


def format_attack(result: dict) -> str:
    r = result["roll"]
    attacker = result["attacker"]
    target = result["target"]

    if result["fumble"]:
        return f"⚔️ {attacker.name} атакует {target.name}...\n💀 КРИТИЧЕСКИЙ ПРОВАЛ! Атака провалилась."

    if not result["hit"]:
        mod_str = f" {'+' + str(r['mod']) if r['mod'] >= 0 else str(r['mod'])}" if r["mod"] else ""
        return f"⚔️ {attacker.name} атакует {target.name}.\n🎲 d20{mod_str} = {r['total']} — Промах! (AC {target.ac})"

    crit_str = "🌟 КРИТ! " if result["crit"] else ""
    return (
        f"⚔️ {attacker.name} атакует {target.name}.\n"
        f"🎲 d20 = {r['natural']} → {r['total']} — Попадание! (AC {target.ac})\n"
        f"{crit_str}Урон: {result['damage']}\n"
        f"❤️ {target.name} HP: {result['target_hp']}/{target.max_hp}"
        + (" — ПОВЕРЖЕН!" if result["target_dead"] else "")
    )
