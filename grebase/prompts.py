from prompt_toolkit import prompt

PROMPT_TEXT = (
    "Select resolution:\n"
    "1. Keep current (this file)\n"
    "2. Keep incoming (this file)\n"
    "3. Keep current (all remaining)\n"
    "4. Keep incoming (all remaining)\n"
    "5. Show diff\n"
    "6. Open editor\n"
    "7. Manual resolve\n"
    "8. Skip\n"
    "9. Abort\n"
    "> "
)


def prompt_conflict_action() -> str:
    return prompt(PROMPT_TEXT).strip()
