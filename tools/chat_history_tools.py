import re
from typing import List, Dict, Optional

def get_user_messages(chat_history: List[Dict[str, str]]) -> List[str]:
    return [
        item.get("content", "")
        for item in chat_history
        if item.get("role") == "user" and item.get("content")
    ]

def answer_chat_history_question(user_input: str, chat_history: List[Dict[str, str]]) -> Optional[str]:
    text = user_input.lower().strip()

    is_history_question = any(phrase in text for phrase in [
        "first message", "first query", "first question", "what did i ask",
        "what was my", "last message", "last query", "previous message", "previous query"
    ])

    number_match = re.search(r"\b(\d+)(st|nd|rd|th)?\s+(message|query|question)\b", text)
    ordinal_match = any(f"{word} message" in text or f"{word} query" in text or f"{word} question" in text for word in [
        "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"
    ])

    if not (is_history_question or number_match or ordinal_match):
        return None

    user_messages = get_user_messages(chat_history)

    if not user_messages:
        return "I do not have any previous user messages in this chat yet."

    if user_messages and user_messages[-1].lower().strip() == text:
        previous_user_messages = user_messages[:-1]
    else:
        previous_user_messages = user_messages

    if not previous_user_messages:
        return "This is the first user message I can see in this chat."

    if any(phrase in text for phrase in [
        "first message",
        "first query",
        "first question",
        "what did i ask first",
        "what was my first"
    ]):
        return f'Your first message was: "{previous_user_messages[0]}"'

    if any(phrase in text for phrase in [
        "last message",
        "last query",
        "previous message",
        "previous query",
        "what did i ask before"
    ]):
        return f'Your previous message was: "{previous_user_messages[-1]}"'

    ordinal_map = {
        "second": 2,
        "third": 3,
        "fourth": 4,
        "fifth": 5,
        "sixth": 6,
        "seventh": 7,
        "eighth": 8,
        "ninth": 9,
        "tenth": 10
    }

    for word, number in ordinal_map.items():
        if f"{word} message" in text or f"{word} query" in text or f"{word} question" in text:
            index = number - 1

            if index < len(previous_user_messages):
                return f'Your {word} message was: "{previous_user_messages[index]}"'

            return f"I can only see {len(previous_user_messages)} previous user message(s) in this chat."

    number_match = re.search(r"\b(\d+)(st|nd|rd|th)?\s+(message|query|question)\b", text)

    if number_match:
        number = int(number_match.group(1))
        index = number - 1

        if index < len(previous_user_messages):
            return f'Your message number {number} was: "{previous_user_messages[index]}"'

        return f"I can only see {len(previous_user_messages)} previous user message(s) in this chat."

    return None
