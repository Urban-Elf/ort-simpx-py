import time
from llama_cpp import Llama
import random
import os
from datetime import date
from rapidfuzz import fuzz
from filter import ProfanityFilter
import json

# ================== CONFIG ==================

SCRIPT_DIR = os.path.dirname(__file__)
MODEL_PATH = os.path.join(
    SCRIPT_DIR,
    "models",
    ""
)
ROOT_CONFIG_PATH = os.path.join(
    SCRIPT_DIR,
    "config.json"
)
CONFIG = None
CONFIG_PATH = None
HISTORY = []

MAX_TURNS = 10 # controls memory size
TEMPERATURE = 0.6
TOP_P = 0.8

class Config:
    def __init__(self, data):
        self.data = data
        self.version = self.get("version", "1.0.0")
        self.timeout_seconds = self.get("idle_timeout_seconds", 30)
        self.max_turns = self.get("max_turns", 10)
        self.temperature_range = self.get("temperature_range", {"low": 0.6, "high": 0.8})
        self.top_p_range = self.get("top_p_range", {"low": 0.7, "high": 0.95})
        self.image_path = self.get("image_path", "")
        self.moods = self.get("moods", {})
        self.sys_prompt_fname = self.get("sys_prompt_fname", "")
        self.cmd_prompt = self.get("cmd_prompt", "")
        self.conversation_tokens = self.get("conversation_tokens", 80)
        self.cmd_tokens = self.get("cmd_tokens", 40)
        self.wake_words = self.get("wake_words", [])
        self.allow_os_commands = self.get("allow_os_commands", False)
        self.shutdown_msg = self.get("shutdown_msg", "Shutting down (v%s).")
        # Populated at parse time
        self.sys_prompt = ""

    def get(self, key, default):
        if key in self.data:
            return self.data[key]
        else:
            print(f"Warning: '{key}' not found in config. Using default value: {default}")
            return default
        
    def has(self, key):
        return key in self.data

if not os.path.exists(ROOT_CONFIG_PATH):
    raise FileNotFoundError(f"Config file not found at {ROOT_CONFIG_PATH}. Please create a config.json with the necessary settings.")

LLM = None

def load_config(path: str):
    global CONFIG, CONFIG_PATH, MODEL_PATH, LLM, MAX_TURNS, TEMPERATURE, TOP_P

    config = None

    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}.")
    with open(path, 'r') as file:
        data = json.load(file)
        config = Config(data)

    # Override model path if specified in config
    model_name = config.get("model", "")
    if config.has("model_path"):
        MODEL_PATH = config.get("model_path", "")
    else:
        MODEL_PATH = os.path.join(SCRIPT_DIR, "models", model_name)
    
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Please check your configuration.")

    # Lock in to new config
    CONFIG = config
    CONFIG_PATH = path

    if LLM is not None:
        LLM.close()

    LLM = Llama(
        model_path=MODEL_PATH,
        n_ctx=CONFIG.get("n_ctx", 1024),
        n_threads=CONFIG.get("n_threads", 4),
        verbose=CONFIG.get("verbose", False)
    )

    HISTORY.clear() # reset memory on config load

    MAX_TURNS = CONFIG.max_turns
    TEMPERATURE = random.uniform(CONFIG.temperature_range["low"], CONFIG.temperature_range["high"])
    TOP_P = random.uniform(CONFIG.top_p_range["low"], CONFIG.top_p_range["high"])

    # Parse prompts
    sys_prompt_path = os.path.join(SCRIPT_DIR, "configs", CONFIG.sys_prompt_fname)
    if os.path.exists(sys_prompt_path):
        with open(sys_prompt_path, 'r') as sp_file:
            CONFIG.sys_prompt = sp_file.read()
    else:
        print(f"Warning: System prompt file '{sys_prompt_path}' not found. Using empty system prompt.")
        CONFIG.sys_prompt = ""

#### LOAD DEFAULT CONFIG ####
def load_default_config():
    with open(ROOT_CONFIG_PATH, 'r') as file:
        data = json.load(file)
        if ("default" not in data) or (not isinstance(data["default"], str)):
            raise ValueError("Config file must contain a 'default' key with the config name as a string.")
        load_config(os.path.join(SCRIPT_DIR, "configs", data["default"]))

# ================== INTENT ==================

SHUTUP_PHRASES = [
    "shut up", "be quiet", "stop talking",
    "stop responding", "go silent", "mute yourself",
    "shut it", "quiet", "enough", "silence",
    "no more", "that's it", "stop now",
    "go away", "leave me alone", "don't respond",
    "hush", "zip it", "button it", "keep quiet",
    "cease and desist", "hold your tongue", "enough already"
]

def fuzzy_match(text, phrases, threshold=80):
    for phrase in phrases:
        if fuzz.partial_ratio(text.lower(), phrase) > threshold:
            return True
    return False

def is_addressing_ort(text: str) -> bool:
    text = text.lower()
    for wake_word in CONFIG.wake_words:
        if wake_word in text:
            return True
    return False

def is_shut_up(text: str) -> bool:
    text = text.lower()

    if "ort" not in text:
        return False

    if any(p in text for p in SHUTUP_PHRASES):
        return True

    return fuzzy_match(text, SHUTUP_PHRASES)

# ================== MEMORY ==================

def trim_memory(history):
    return history[-MAX_TURNS:]

# we do NOT rely on system staying in memory implicitly
def build_messages(history):
    return [
        {"role": "system", "content": CONFIG.sys_prompt},
        *history
    ]

# ================== LLM ==================

profanity_filter = ProfanityFilter()

def get_response(user_input: str):
    global HISTORY

    HISTORY.append({"role": "user", "content": user_input})

    # trim memory (IMPORTANT)
    history = trim_memory(HISTORY)

    messages = build_messages(history)

    output = LLM.create_chat_completion(
        messages=messages,
        max_tokens=CONFIG.conversation_tokens,
        temperature=TEMPERATURE,
        top_p=TOP_P
    )

    reply = output["choices"][0]["message"]["content"]

    history.append({"role": "llm", "content": reply})

    return profanity_filter.filter_text(reply.strip())

def get_command_response(user_input: str):
    messages = [
        # Commanding prompt
        {"role": "system", "content": CONFIG.sys_prompt + "\n" + CONFIG.cmd_prompt},
        {"role": "user", "content": user_input}
    ]

    output = LLM.create_chat_completion(
        messages=messages,
        max_tokens=CONFIG.cmd_tokens,  # shorter for commands
        temperature=TEMPERATURE,
        top_p=TOP_P
    )

    reply = output["choices"][0]["message"]["content"].strip()
    return profanity_filter.filter_text(reply)

# ================== CONTROL ==================

ORT_ACTIVE = False
ORT_MUTED = False
LAST_ADDRESSED = 0

def should_respond(user_input: str):
    global ORT_ACTIVE, ORT_MUTED, LAST_ADDRESSED

    result = {
        "respond": False,
        "response": None
    }
    now = time.time()

    # timeout reset
    if now - LAST_ADDRESSED > CONFIG.timeout_seconds:
        ORT_ACTIVE = False

    # shut up command
    if is_shut_up(user_input):
        ORT_MUTED = True
        ORT_ACTIVE = False
        result["respond"] = False
        result["response"] = get_command_response(user_input)
        return result

    # wake word
    if is_addressing_ort(user_input):
        ORT_ACTIVE = True
        ORT_MUTED = False
        LAST_ADDRESSED = now
        result["respond"] = True
        return result

    # continue convo
    if ORT_ACTIVE and not ORT_MUTED:
        LAST_ADDRESSED = now
        result["respond"] = True
        return result

    return result

# ================== LOOP ==================

if __name__ == "__main__":
    load_default_config()

    print("Ort is awake. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        result = should_respond(user_input)

        if result["respond"]: # should respond
            print(get_response(user_input))
        else:
            if result["response"] is not None:
                print(result["response"])
