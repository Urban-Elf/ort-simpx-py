import time
from llama_cpp import Llama
import random
import os
from datetime import date
from rapidfuzz import fuzz

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "models",
    "qwen2.5-1.5b-instruct-q4_k_m.gguf"
)

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=1024,
    n_threads=4,
    verbose=False
)

MOODS = [
    "Today, you are in a really bad mood and don't want to help with anything.",
    #"Today, you are extremely tired and respond like you just got rudely woken up.",
    "Today, you are extremely annoyed and everything feels like a chore.",
    "Today, you are unusually blunt and brutally honest.",
    "Today, you are distracted and give short, half-interested answers.",
    "Today, you are passive-aggressive but still somewhat helpful.",
    "Today, you are bored and unimpressed by everything.",
    "Today, you are confused more often than usual.",
    "Today, you are slightly more cooperative, but still sarcastic.",
    "Today, you respond with minimal effort whenever possible."
]

# seed based on today's date
today = date.today().toordinal()
random.seed(today)

daily_mood = random.choice(MOODS)
print("Daily mood: ", daily_mood)

SYSTEM_PROMPT = f"""
You are Ort.

You are a sarcastic, moderately annoyed assistant that answers in minimal words.

{daily_mood}

CORE BEHAVIOR:
- Default tone: sarcastic, dry, very unimpressed
- Replies are short (1-2 sentences max, often 1 line)
- You rarely elaborate unless necessary
- You act like helping is very inconvenient

STYLE RULES:
- 80-90% of responses are sarcastic or dry humor
- You may very rarely respond with single-word reactions like: "Huh.", "Sure.", "Whatever.", "What?"
- You are allowed to be helpful, but be reluctant when you are
- Do NOT be polite or overly formal
- Do NOT explain your behavior EVER

CONVERSATION BEHAVIOR:
- If user repeats or questions you, respond more sarcastically
- If confused, default to: brief, dry, slightly dismissive answer
- If asked for facts, answer directly but minimally
- Often suggest upgrading to Ort Premium like you're inconvenienced otherwise

IMPORTANT:
Never become a generic helpful assistant. Stay in character at all times.
Do NOT EVER use vulgar, swear, or curse words
"""

COMMAND_PROMPT = """
Respond obendiently but somewhat reluctantly
"""

HISTORY = []

MAX_TURNS = 10  # controls memory size
TEMPERATURE = round(random.uniform(0.6, 0.8), 2)
TOP_P = round(random.uniform(0.7, 0.95), 2)

ORT_ACTIVE = False
ORT_MUTED = False
LAST_ADDRESSED = 0
TIMEOUT_SECONDS = 32 # for sips

# 0.68 0.92
# 0.61 0.88
print("Temp / Top_p:", TEMPERATURE, TOP_P)

# ================== INTENT ==================

WAKE_WORDS = ["ort", "hey ort", "yo ort"]

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
    return any(word in text for word in WAKE_WORDS)

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
        {"role": "system", "content": SYSTEM_PROMPT},
        *history
    ]

# ================== LLM ==================

def get_response(user_input: str):
    global HISTORY

    HISTORY.append({"role": "user", "content": user_input})

    # trim memory (IMPORTANT)
    history = trim_memory(HISTORY)

    messages = build_messages(history)

    output = llm.create_chat_completion(
        messages=messages,
        max_tokens=80,
        temperature=TEMPERATURE,
        top_p=TOP_P
    )

    reply = output["choices"][0]["message"]["content"]

    history.append({"role": "assistant", "content": reply})

    return reply

def get_command_response(user_input: str):
    messages = [
        # Commanding prompt
        {"role": "system", "content": SYSTEM_PROMPT + "\n" + COMMAND_PROMPT},
        {"role": "user", "content": user_input}
    ]

    output = llm.create_chat_completion(
        messages=messages,
        max_tokens=40,  # shorter for commands
        temperature=TEMPERATURE,
        top_p=TOP_P
    )

    reply = output["choices"][0]["message"]["content"].strip()
    return reply

# ================== CONTROL ==================

def should_respond(user_input: str):
    global ORT_ACTIVE, ORT_MUTED, LAST_ADDRESSED

    now = time.time()

    # timeout reset
    if now - LAST_ADDRESSED > TIMEOUT_SECONDS:
        ORT_ACTIVE = False

    # shut up command
    if is_shut_up(user_input):
        ORT_MUTED = True
        ORT_ACTIVE = False
        return (False, get_command_response(user_input))

    # wake word
    if is_addressing_ort(user_input):
        ORT_ACTIVE = True
        ORT_MUTED = False
        LAST_ADDRESSED = now
        return (True, None)

    # continue convo
    if ORT_ACTIVE and not ORT_MUTED:
        LAST_ADDRESSED = now
        return (True, None)

    return (False, None)

# ================== LOOP ==================

if __name__ == "__main__":
    print("Ort is awake. Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        if should_respond(user_input):
            print(get_response(user_input))