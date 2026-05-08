import re

# Time for a Caeser cipher.

A = "z"
B = "y"
C = "x"
D = "w"
E = "v"
F = "u"
G = "t"
H = "s"
I = "r"
J = "q"
K = "p"
L = "o"
M = "n"
N = "m"
O = "l"
P = "k"
Q = "j"
R = "i"
S = "h"
T = "g"
U = "f"
V = "e"
W = "d"
X = "c"
Y = "b"
Z = "a"

BANNED_WORDS = [
    T+L+W+W+Z+N+M,
    L+N+T,
    L+N+U+T,
    L+N+O,
    L+N+U+O,

    # f
    U+F+X+P,
    U+F+X+P+V+I,
    U+F+X+P+R+M+T,
    U+F+X+P+V+W,

    # s
    H+S+R+G,
    H+S+R+G+G+B,
    Y+F+O+O+H+S+R+G,

    # b
    Y+R+G+X+S,
    Y+R+G+X+S+V+H,
    Y+R+G+X+S+V+H+Z+H+H,
    Y+Z+H+G+Z+I+W,

    # a
    Z+H+H,
    Z+H+H+S+L+O+V,
    W+F+N+Y+Z+H+H,

    # s
    W+R+X+P,
    X+L+X+P,
    K+F+H+H+B,

    G+R+G+H,
    G+R+G+G+R+V+H,
    Y+L+L+Y,
    Y+L+L+Y+H,
    Y+L+L+Y+R+V+H,

    X+F+N,
    X+F+N+N+R+M+T,

    # i
    H+O+F+G,
    D+S+L+I+V,
    H+P+Z+M+P,

    R+W+R+L+G,
    N+L+I+L+M,

    # l
    X+I+Z+K,
    W+Z+N+M,
    W+Z+N+N+R+G,
    S+V+O+O,
]

class ProfanityFilter:
    def __init__(self, bad_words=BANNED_WORDS):
        self.bad_words = [word.lower() for word in (bad_words or [])]
        self.patterns = {}
        
        for word in self.bad_words:
            self.patterns[word] = self._create_detection_pattern(word)
    
    def _create_detection_pattern(self, word: str) -> re.Pattern:
        # Character substitutions map
        subs = {
            'a': r'[a@*]',
            'i': r'[i!1*]',
            'e': r'[e3*]',
            'o': r'[o0*]',
            's': r'[s$5*]',
            't': r'[t7*]'
        }
        
        parts = []
        for char in word:
            p = subs.get(char, f'[{re.escape(char)}*]')
            parts.append(p)
        
        # Allow for optional separators like '-' or '.' between letters
        separator = r'[-_.\s]*'
        core = separator.join(parts)
        
        # Boundary logic: Lookbehind and Lookahead
        boundary_start = r'(?:^|(?<=[^a-zA-Z0-9]))'
        boundary_end = r'(?=[^a-zA-Z0-9]|$)'
        
        pattern = f'{boundary_start}{core}{boundary_end}'
        return re.compile(pattern, re.IGNORECASE)
    
    def contains_profanity(self, text: str) -> bool:
        if not text:
            return False
        return any(pattern.search(text) for pattern in self.patterns.values())
    
    def filter_text(self, text: str, mask_char: str = "#") -> str:
        """Replaces profane content with repeated mask_char based on match length."""
        if not text:
            return text
        
        final_text = text
        
        # This function is called for every match found
        def masker(match):
            return mask_char * len(match.group(0))
        
        for pattern in self.patterns.values():
            # re.sub can take a function (masker) as the replacement argument
            final_text = pattern.sub(masker, final_text)
            
        return final_text

if __name__ == "__main__":
    prof_filter = ProfanityFilter(bad_words=BANNED_WORDS)
    
    # Replace x with actual words if testing
    tests = [
        "xxxx it",                     # Filter
        "exxxame",                     # Clean (The "e" and "m" wrap it)
        "e-xxxx-e",                   # Filter (hyphens are boundaries)
        "x*xx",                        # Filter
        "x**x",                        # Filter
        "x***",                        # Filter
        "what the xxxx",          # Filter
        "Xxxx!",                       # Filter
        "X-X-X-X",                     # Filter
        "this is exxxxxe cake",        # Clean
        "This is a xxxx stupid game, xxxx it!" # Filter (two counts)
    ]
    
    print(f"{'Input Text':<40} | {'Result'}")
    print("-" * 60)
    for test in tests:
        res = prof_filter.filter_text(test) if prof_filter.contains_profanity(test) else "clean"
        print(f"{test:<40} | {res}")

    while True:
        user_input = input("Enter text to check for profanity (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            break
        if prof_filter.contains_profanity(user_input):
            print("Filtered text:")
            print(prof_filter.filter_text(user_input))
        else:
            print("Text is clean.")