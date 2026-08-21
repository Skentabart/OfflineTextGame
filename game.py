import urllib.request
import urllib.error
import os
import sys
import json
import random
import subprocess
import tempfile
import re
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).resolve().parent

CONFIG_FILE = ROOT / "config.json"
SAVE_DIR = ROOT / "saves"
MODEL_DIR = ROOT / "model"
BIN_DIR = ROOT / "bin"

SAVE_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)
BIN_DIR.mkdir(exist_ok=True)


# ============================================================
# CONFIG
# ============================================================

DEFAULT_CONFIG = {
    "model": "model/Qwen3-1.7B-Q4_K_M.gguf",

    "llama_cli": "bin/llama-cli.exe",

    "context": 4096,
    "threads": 8,
    "gpu_layers": 0,

    "temperature": 0.8,
    "top_p": 0.9,
    "top_k": 40,

    "max_tokens": 250
}


def load_config():
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        result = DEFAULT_CONFIG.copy()
        result.update(config)

        return result

    except Exception:
        return DEFAULT_CONFIG.copy()


CONFIG = load_config()


# ============================================================
# PATHS
# ============================================================

MODEL_PATH = ROOT / CONFIG["model"]
LLAMA_PATH = ROOT / CONFIG["llama_cli"]


# ============================================================
# GAME STATE
# ============================================================

def new_game():

    return {
        "player": {
            "name": "Игрок",
            "health": 100,
            "max_health": 100,
            "energy": 100,
            "max_energy": 100,
            "location": "Заброшенная станция",
            "inventory": [
                "старый фонарь",
                "нож"
            ]
        },

        "world": {
            "time": "22:15",
            "weather": "дождь",
            "danger": 10
        },

        "flags": {
            "door_open": False,
            "generator_started": False,
            "met_stranger": False,
            "found_key": False
        },

        "history": [],

        "turn": 0
    }


game = new_game()


# ============================================================
# COLORS
# ============================================================

class Color:

    RESET = "\033[0m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"

    WHITE = "\033[97m"


def enable_colors():

    if os.name == "nt":

        os.system("")


enable_colors()


def c(text, color):

    return color + str(text) + Color.RESET


# ============================================================
# SAVE / LOAD
# ============================================================

def save_game(slot=1):

    path = SAVE_DIR / f"save{slot}.json"

    try:

        with open(path, "w", encoding="utf-8") as f:

            json.dump(
                game,
                f,
                indent=4,
                ensure_ascii=False
            )

        print(c(f"\nИгра сохранена: слот {slot}\n", Color.GREEN))

    except Exception as e:

        print(c(f"Ошибка сохранения: {e}", Color.RED))


def load_game(slot=1):

    global game

    path = SAVE_DIR / f"save{slot}.json"

    if not path.exists():

        print(c(
            f"\nСохранение {slot} не найдено.\n",
            Color.YELLOW
        ))

        return False

    try:

        with open(path, "r", encoding="utf-8") as f:

            game = json.load(f)

        print(c(
            f"\nИгра загружена из слота {slot}.\n",
            Color.GREEN
        ))

        return True

    except Exception as e:

        print(c(
            f"\nОшибка загрузки: {e}\n",
            Color.RED
        ))

        return False


# ============================================================
# GAME STATE
# ============================================================

def player_status():

    p = game["player"]

    print()
    print(c("════════════════════════════════════", Color.CYAN))
    print(c(" СОСТОЯНИЕ ПЕРСОНАЖА", Color.CYAN))
    print(c("════════════════════════════════════", Color.CYAN))

    print(f"Здоровье : {p['health']}/{p['max_health']}")
    print(f"Энергия  : {p['energy']}/{p['max_energy']}")
    print(f"Место    : {p['location']}")
    print(f"Время    : {game['world']['time']}")
    print(f"Погода   : {game['world']['weather']}")

    print()
    print("Инвентарь:")

    if p["inventory"]:

        for item in p["inventory"]:

            print(" •", item)

    else:

        print(" • пусто")

    print()


def inventory():

    print()

    if not game["player"]["inventory"]:

        print("Инвентарь пуст.")

        return

    print(c("ИНВЕНТАРЬ", Color.YELLOW))

    for i, item in enumerate(
        game["player"]["inventory"],
        1
    ):

        print(f"{i}. {item}")

    print()


# ============================================================
# TIME
# ============================================================

def advance_time(minutes=10):

    current = game["world"]["time"]

    try:

        h, m = map(int, current.split(":"))

    except:

        h, m = 22, 15

    total = h * 60 + m + minutes

    total %= 24 * 60

    h = total // 60
    m = total % 60

    game["world"]["time"] = f"{h:02d}:{m:02d}"


# ============================================================
# RANDOM EVENTS
# ============================================================

def random_event():

    danger = game["world"]["danger"]

    chance = min(30, 5 + danger // 4)

    if random.randint(1, 100) > chance:

        return ""

    events = [

        "Где-то неподалёку раздаётся металлический скрежет.",

        "В темноте что-то быстро пробегает мимо.",

        "Фонарь на мгновение начинает мерцать.",

        "Ты слышишь тихие шаги за стеной.",

        "Вдалеке хлопает дверь.",

        "На несколько секунд становится совершенно тихо."

    ]

    return random.choice(events)


# ============================================================
# WORLD RULES
# ============================================================

def get_world_state():

    return {
        "location": game["player"]["location"],
        "health": game["player"]["health"],
        "energy": game["player"]["energy"],
        "inventory": game["player"]["inventory"],
        "time": game["world"]["time"],
        "weather": game["world"]["weather"],
        "danger": game["world"]["danger"],
        "flags": game["flags"]
    }


# ============================================================
# SIMPLE GAME LOGIC
# ============================================================

def process_action(action):

    action_lower = action.lower()

    p = game["player"]
    flags = game["flags"]

    events = []

    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if action_lower in [
        "помощь",
        "help",
        "?",
        "команды"
    ]:

        return (
            "Можно писать действия свободным текстом.\n\n"
            "Например:\n"
            " • осмотреть комнату\n"
            " • открыть дверь\n"
            " • взять ключ\n"
            " • включить фонарь\n"
            " • идти на север\n"
            " • поговорить с человеком\n"
            " • использовать нож\n\n"
            "Системные команды:\n"
            " /save\n"
            " /load\n"
            " /status\n"
            " /inventory\n"
            " /quit"
        )

    # --------------------------------------------------------
    # INVENTORY
    # --------------------------------------------------------

    if any(x in action_lower for x in [
        "инвентарь",
        "рюкзак",
        "вещи"
    ]):

        inventory()

        return None

    # --------------------------------------------------------
    # OPEN DOOR
    # --------------------------------------------------------

    if any(x in action_lower for x in [
        "открыть дверь",
        "открываю дверь",
        "дверь открыть"
    ]):

        if flags["door_open"]:

            return "Дверь уже открыта."

        if flags["found_key"]:

            flags["door_open"] = True

            p["energy"] = max(
                0,
                p["energy"] - 5
            )

            game["world"]["danger"] += 5

            return (
                "Ты вставляешь найденный ключ в замок. "
                "После нескольких попыток дверь наконец открывается."
            )

        return (
            "Дверь заперта. "
            "Похоже, нужен ключ."
        )

    # --------------------------------------------------------
    # FIND KEY
    # --------------------------------------------------------

    if any(x in action_lower for x in [
        "искать ключ",
        "найти ключ",
        "ищу ключ",
        "осмотреть стол"
    ]):

        if flags["found_key"]:

            return "Ты уже нашёл ключ."

        flags["found_key"] = True

        p["inventory"].append("старый ключ")

        p["energy"] = max(
            0,
            p["energy"] - 8
        )

        return (
            "После нескольких минут поисков "
            "ты находишь старый ключ под металлической коробкой."
        )

    # --------------------------------------------------------
    # FLASHLIGHT
    # --------------------------------------------------------

    if any(x in action_lower for x in [
        "фонарь",
        "включить свет",
        "включаю фонарь"
    ]):

        if "старый фонарь" not in p["inventory"]:

            return "У тебя нет фонаря."

        p["energy"] = max(
            0,
            p["energy"] - 1
        )

        return (
            "Ты включаешь фонарь. "
            "Узкий луч прорезает темноту."
        )

    # --------------------------------------------------------
    # REST
    # --------------------------------------------------------

    if any(x in action_lower for x in [
        "отдохнуть",
        "спать",
        "сесть",
        "отдыхаю"
    ]):

        p["energy"] = min(
            p["max_energy"],
            p["energy"] + 30
        )

        advance_time(30)

        return (
            "Ты немного отдыхаешь. "
            "Силы постепенно возвращаются."
        )

    # --------------------------------------------------------
    # MOVE
    # --------------------------------------------------------

    directions = [
        "север",
        "юг",
        "восток",
        "запад",
        "north",
        "south",
        "east",
        "west"
    ]

    if any(x in action_lower for x in directions):

        p["energy"] = max(
            0,
            p["energy"] - 10
        )

        game["world"]["danger"] += random.randint(
            0,
            2
        )

        advance_time(10)

        return (
            "Ты осторожно двигаешься дальше. "
            "Старая станция продолжается за пределами "
            "освещённого участка."
        )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if any(x in action_lower for x in [
        "осмотреть",
        "исследовать",
        "осматриваю",
        "ищу",
        "поискать"
    ]):

        p["energy"] = max(
            0,
            p["energy"] - 5
        )

        advance_time(5)

        return (
            "Ты внимательно осматриваешь окружающее пространство. "
            "Пыль покрывает пол, а стены исписаны "
            "старыми предупреждениями."
        )

    # --------------------------------------------------------
    # TALK
    # --------------------------------------------------------

    if any(x in action_lower for x in [
        "поговорить",
        "спросить",
        "разговор",
        "человек",
        "незнакомец"
    ]):

        flags["met_stranger"] = True

        return (
            "Из тёмного коридора доносится голос:\n\n"
            "— Не стоит здесь задерживаться..."
        )

    # --------------------------------------------------------
    # ATTACK
    # --------------------------------------------------------

    if any(x in action_lower for x in [
        "атаковать",
        "ударить",
        "напасть",
        "убить"
    ]):

        damage = random.randint(
            5,
            20
        )

        game["world"]["danger"] += 10

        return (
            f"Ты совершаешь резкое движение. "
            f"Ситуация становится опаснее. "
            f"Урон: {damage}."
        )

    return None


# ============================================================
# AI PROMPT
# ============================================================

def build_prompt(action, rule_result):

    state = get_world_state()

    recent_history = game["history"][-6:]

    history_text = ""

    for item in recent_history:

        history_text += (
            f"Игрок: {item['player']}\n"
            f"Мир: {item['world']}\n\n"
        )

    prompt = f"""
Ты — ведущий текстовой офлайн-игры.

Название игры: OFFLINE GAME.

Жанр:
постапокалиптический хоррор / исследование.

Ты НЕ должен говорить, что ты нейросеть.

Ты являешься рассказчиком игрового мира.

ВАЖНЫЕ ПРАВИЛА:

1. Не придумывай невозможные действия игрока.
2. Не меняй характеристики персонажа самовольно.
3. Не создавай предметы из ничего.
4. Не телепортируй игрока.
5. Не убивай игрока без причины.
6. Не управляй персонажем вместо игрока.
7. Отвечай на русском языке.
8. Пиши художественно, но кратко.
9. Обычно 2-5 абзацев.
10. Не используй Markdown-заголовки.
11. Не описывай мысли игрока.
12. Описывай только мир, события и последствия действия.

ТЕКУЩЕЕ СОСТОЯНИЕ:

{json.dumps(state, ensure_ascii=False, indent=2)}

ПОСЛЕДНИЕ СОБЫТИЯ:

{history_text}

ДЕЙСТВИЕ ИГРОКА:

{action}

ВНУТРЕННЯЯ ЛОГИКА ИГРЫ:

{rule_result if rule_result else "Специальное правило не сработало."}

Сформируй художественное описание результата действия игрока.

Не повторяй само действие.

Не добавляй игровые характеристики вроде HP или энергии,
если это не требуется сюжетом.

Ответ должен быть только текстом игрового мира.
"""

    return prompt.strip()


# ============================================================
# AI
# ============================================================

def check_ai():

    try:

        request = urllib.request.Request(
            "http://127.0.0.1:8080/health",
            method="GET"
        )

        with urllib.request.urlopen(
            request,
            timeout=3
        ) as response:

            if response.status == 200:

                return True

    except:

        pass

    print(
        c(
            "\nЛокальная AI модель не запущена.",
            Color.RED
        )
    )

    print(
        "Запусти игру через start.bat."
    )

    return False


def run_ai(prompt):

    server_url = "http://127.0.0.1:8080"

    try:

        data = {
            "model": "Qwen3-1.7B",

            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты — рассказчик текстовой игры. "
                        "Отвечай только художественным описанием "
                        "происходящего в игровом мире. "
                        "Не рассуждай вслух. "
                        "Не объясняй свои решения. "
                        "Не анализируй задачу. "
                        "Не пиши внутренние мысли. "
                        "Не используй <think>. "
                        "Сразу выдавай готовый игровой текст."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            "temperature": float(CONFIG["temperature"]),
            "top_p": float(CONFIG["top_p"]),
            "top_k": int(CONFIG["top_k"]),

            "max_tokens": int(CONFIG["max_tokens"]),

            "stream": False,

            "reasoning": False,

            "chat_template_kwargs": {
                "enable_thinking": False
            }
        }

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        request = urllib.request.Request(
            server_url + "/v1/chat/completions",

            data=body,

            headers={
                "Content-Type": "application/json"
            },

            method="POST"
        )

        print(
            c(
                "  [AI] Генерация...",
                Color.YELLOW
            )
        )

        with urllib.request.urlopen(
            request,
            timeout=180
        ) as response:

            raw = response.read()

        result = json.loads(
            raw.decode(
                "utf-8",
                errors="replace"
            )
        )

        # ----------------------------------------------------
        # Проверяем ошибку API
        # ----------------------------------------------------

        if "error" in result:

            error = result["error"]

            if isinstance(error, dict):

                message = error.get(
                    "message",
                    str(error)
                )

            else:

                message = str(error)

            print()

            print(
                c(
                    "[AI] Ошибка сервера: " + message,
                    Color.RED
                )
            )

            return None

        # ----------------------------------------------------
        # Получаем ответ
        # ----------------------------------------------------

        choices = result.get(
            "choices",
            []
        )

        if not choices:

            print()

            print(
                c(
                    "[AI] Сервер не вернул choices.",
                    Color.RED
                )
            )

            return None

        message = choices[0].get(
            "message",
            {}
        )

        output = message.get(
            "content",
            ""
        )

        if output is None:

            output = ""

        output = str(output)

        # ----------------------------------------------------
        # На случай если reasoning всё-таки попал в content
        # ----------------------------------------------------

        output = re.sub(
            r"<think>.*?</think>",
            "",
            output,
            flags=re.DOTALL | re.IGNORECASE
        )

        output = re.sub(
            r"<think>.*",
            "",
            output,
            flags=re.DOTALL | re.IGNORECASE
        )

        # Иногда модель сама пишет подобные фразы.
        # Убираем только явные служебные конструкции.

        output = re.sub(
            r"^(Хорошо,?\s*)?давай\s+подумаем.*?(?=\n\n|\n|$)",
            "",
            output,
            flags=re.DOTALL | re.IGNORECASE
        )

        output = output.strip()

        if not output:

            print()

            print(
                c(
                    "[AI] Пустой ответ.",
                    Color.RED
                )
            )

            return None

        return output

    except urllib.error.HTTPError as e:

        try:

            error_text = e.read().decode(
                "utf-8",
                errors="replace"
            )

        except:

            error_text = str(e)

        print()

        print(
            c(
                f"[AI] HTTP ошибка {e.code}",
                Color.RED
            )
        )

        print(error_text)

        return None

    except urllib.error.URLError as e:

        print()

        print(
            c(
                "[AI] Не удалось подключиться к локальной модели.",
                Color.RED
            )
        )

        print(
            "Убедись, что llama-server запущен."
        )

        print(
            f"Ошибка: {e}"
        )

        return None

    except TimeoutError:

        print()

        print(
            c(
                "[AI] Тайм-аут генерации.",
                Color.RED
            )
        )

        return None

    except Exception as e:

        print()

        print(
            c(
                f"[AI] Ошибка: {e}",
                Color.RED
            )
        )

        return None
# ============================================================
# FALLBACK
# ============================================================

def fallback_response(action):

    responses = [

        "Ты осторожно выполняешь действие. Окружающая тишина кажется подозрительной.",

        "Несколько секунд ничего не происходит. Затем где-то неподалёку раздаётся тихий звук.",

        "Ты внимательно осматриваешь результат своих действий. Пока ничего необычного не происходит.",

        "Окружение отвечает на твои действия едва заметным изменением звука и света."

    ]

    return random.choice(responses)


# ============================================================
# TURN
# ============================================================

def perform_action(action):

    if not action.strip():

        return

    rule_result = process_action(action)

    if rule_result is None:

        rule_result = ""

    # If it is a system-like action that already has a complete answer

    system_actions = [

        "помощь",
        "help",
        "?",
        "команды"
    ]

    if action.lower().strip() in system_actions:

        print()
        print(rule_result)
        print()

        return

    # --------------------------------------------------------
    # AI
    # --------------------------------------------------------

    prompt = build_prompt(
        action,
        rule_result
    )

    print()
    print(c(
        "▌ Рассказчик:",
        Color.MAGENTA
    ))

    response = run_ai(prompt)

    if not response:

        response = rule_result

    if not response:

        response = fallback_response(
            action
        )

    print()
    print(response)
    print()

    # --------------------------------------------------------
    # Event
    # --------------------------------------------------------

    event = random_event()

    if event:

        print(c(
            "⚠ " + event,
            Color.YELLOW
        ))

        print()

    # --------------------------------------------------------
    # History
    # --------------------------------------------------------

    game["history"].append({

        "player": action,

        "world": response,

        "time": game["world"]["time"]

    })

    game["turn"] += 1

    advance_time(5)


# ============================================================
# INTRO
# ============================================================

def intro():

    os.system("cls" if os.name == "nt" else "clear")

    print()
    print(c(
        "███████╗ ███████╗ ██████╗ ",
        Color.CYAN
    ))

    print(c(
        "██╔════╝ ██╔════╝██╔════╝ ",
        Color.CYAN
    ))

    print(c(
        "█████╗   █████╗  ██║  ███╗",
        Color.CYAN
    ))

    print(c(
        "██╔══╝   ██╔══╝  ██║   ██║",
        Color.CYAN
    ))

    print(c(
        "██║      ███████╗╚██████╔╝",
        Color.CYAN
    ))

    print(c(
        "╚═╝      ╚══════╝ ╚═════╝ ",
        Color.CYAN
    ))

    print()
    print(
        c(
            "OFFLINE TEXT ADVENTURE",
            Color.YELLOW
        )
    )

    print()
    print(
        "Локальная нейросеть • Без интернета • Без сервера"
    )

    print()
    print(
        "Ты приходишь в себя на заброшенной станции."
    )

    print(
        "За окнами идёт сильный дождь."
    )

    print(
        "Свет давно отключён."
    )

    print(
        "Перед тобой находится старая металлическая дверь."
    )

    print()
    print(
        c(
            "Что будешь делать?",
            Color.GREEN
        )
    )

    print()


# ============================================================
# MENU
# ============================================================

def main_menu():

    while True:

        try:

            action = input(
                c(
                    ">>> ",
                    Color.GREEN
                )
            ).strip()

        except KeyboardInterrupt:

            print("\n")

            break

        except EOFError:

            break

        if not action:

            continue

        # ----------------------------------------------------
        # QUIT
        # ----------------------------------------------------

        if action.lower() in [
            "/quit",
            "/exit",
            "выход"
        ]:

            print(
                "\nДо встречи."
            )

            break

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        if action.lower().startswith("/save"):

            parts = action.split()

            slot = 1

            if len(parts) > 1:

                try:
                    slot = int(parts[1])
                except:
                    slot = 1

            save_game(slot)

            continue

        # ----------------------------------------------------
        # LOAD
        # ----------------------------------------------------

        if action.lower().startswith("/load"):

            parts = action.split()

            slot = 1

            if len(parts) > 1:

                try:
                    slot = int(parts[1])
                except:
                    slot = 1

            load_game(slot)

            continue

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if action.lower() in [
            "/status",
            "/stats"
        ]:

            player_status()

            continue

        # ----------------------------------------------------
        # INVENTORY
        # ----------------------------------------------------

        if action.lower() in [
            "/inventory",
            "/inv"
        ]:

            inventory()

            continue

        # ----------------------------------------------------
        # HELP
        # ----------------------------------------------------

        if action.lower() in [
            "/help",
            "/commands"
        ]:

            print()
            print(
                "Команды:"
            )

            print(
                "/save [слот]"
            )

            print(
                "/load [слот]"
            )

            print(
                "/status"
            )

            print(
                "/inventory"
            )

            print(
                "/quit"
            )

            print()

            continue

        # ----------------------------------------------------
        # GAME ACTION
        # ----------------------------------------------------

        perform_action(action)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    intro()

    if not MODEL_PATH.exists():

        print(c(
            "\nВНИМАНИЕ: модель не найдена.",
            Color.YELLOW
        ))

        print(
            "Запусти setup.bat для установки модели."
        )

        print()

    if not LLAMA_PATH.exists():

        print(c(
            "ВНИМАНИЕ: llama-cli.exe не найден.",
            Color.YELLOW
        ))

        print(
            "Запусти setup.bat."
        )

        print()

    main_menu()