"""Lightweight voice text parsing without external heavy dependencies."""

import re
from datetime import datetime, timedelta
from typing import Dict, Any


_INCOME_KEYWORDS = {
    "salary",
    "bonus",
    "deposit",
    "credit",
    "refunded",
    "refund",
    "received",
    "income",
}

_CATEGORY_KEYWORDS = {
    "salary": "Salary",
    "deposit": "Salary",
    "bonus": "Salary",
    "food": "Food",
    "restaurant": "Food",
    "dining": "Food",
    "rent": "Rent",
    "shopping": "Shopping",
    "grocery": "Groceries",
    "groceries": "Groceries",
    "supermarket": "Groceries",
    "subscription": "Subscription",
    "netflix": "Subscription",
    "spotify": "Subscription",
    "electricity": "Bills",
    "water": "Bills",
    "internet": "Bills",
    "insurance": "Insurance",
    "health": "Insurance",
    "fuel": "Transport",
    "car": "Transport",
    "bus": "Transport",
    "taxi": "Transport",
    "uber": "Transport",
    "ola": "Transport",
    "loan": "Loans",
    "emi": "Loans",
    "mortgage": "Loans",
    "gift": "Gift",
    "donation": "Donation",
    "charity": "Donation",
    "entertainment": "Entertainment",
    "movie": "Entertainment",
    "concert": "Entertainment",
    "travel": "Travel",
    "flight": "Travel",
    "hotel": "Travel",
    "vacation": "Travel",
}

_CURRENCY_WORDS = ["rs", "rupees", "inr", "₹", "rs."]


def _extract_amount(text: str) -> float | None:
    """Pick the first numeric amount in the text."""
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _detect_date(text: str) -> str:
    """Return an ISO date string based on simple keywords."""
    today = datetime.now().date()
    lowered = text.lower()
    if "yesterday" in lowered:
        return (today - timedelta(days=1)).isoformat()
    if "tomorrow" in lowered:
        return (today + timedelta(days=1)).isoformat()
    return today.isoformat()


def _clean_description(text: str) -> str:
    """Remove currency words and numbers, leaving a concise description."""
    lowered = text.lower()
    for word in _CURRENCY_WORDS:
        lowered = lowered.replace(word, " ")
    lowered = re.sub(r"[₹$,]", " ", lowered)
    lowered = re.sub(r"\b[0-9]+(?:\.[0-9]+)?\b", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _infer_category(words: list[str]) -> str | None:
    for word in words:
        if word in _CATEGORY_KEYWORDS:
            return _CATEGORY_KEYWORDS[word]
    return None


def process_voice_transaction(voice_text: str) -> Dict[str, Any]:
    """Parse voice text into structured hints (amount, type, category, date)."""
    if not isinstance(voice_text, str):
        return {
            "amount": None,
            "transaction_type": "expense",
            "category_hint": None,
            "cleaned_description": "",
            "date": datetime.now().date().isoformat(),
        }

    normalized = voice_text.lower()
    words = re.findall(r"[a-zA-Z]+", normalized)
    amount = _extract_amount(normalized)
    date_guess = _detect_date(normalized)
    description = _clean_description(normalized)

    is_income = any(word in _INCOME_KEYWORDS for word in words)
    category_hint = _infer_category(words)

    return {
        "amount": amount,
        "transaction_type": "income" if is_income else "expense",
        "category_hint": category_hint,
        "cleaned_description": description or voice_text.strip(),
        "date": date_guess,
    }
