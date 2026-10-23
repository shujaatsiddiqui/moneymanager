"""AI categorization using Ollama."""

import re
from typing import Optional

import requests

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "moneymanager"  # Custom model with categorization context


class AICategorizer:
    """AI-powered transaction categorization using Ollama."""

    def __init__(self, url: str = OLLAMA_URL, model: str = OLLAMA_MODEL):
        self.url = url
        self.model = model

    def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            resp = requests.get(f"{self.url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            pass
        return False

    def suggest_rule_pattern(self, description: str) -> Optional[str]:
        """Use Ollama to suggest a good rule pattern for a transaction description."""
        prompt = f"""Extract the merchant/company name from this transaction description. Return ONLY the core merchant name that would match similar transactions.

Examples:
- "STARBUCKS STORE #12345 NEW YORK" → "STARBUCKS"
- "AMAZON.COM*1A2B3C4D5" → "AMAZON"
- "TST* URBAN BIRD 026" → "TST* URBAN BIRD"
- "WM SUPERCENTER #2918" → "WM SUPERCENTER"
- "INDIA METRO SUPERMARKET" → "INDIA METRO"
- "Zelle payment to JOHN DOE" → "Zelle payment to"

Transaction: "{description}"

Return ONLY the pattern (no quotes, no explanation):"""

        try:
            resp = requests.post(
                f"{self.url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=30
            )
            if resp.status_code == 200:
                result = resp.json().get("response", "").strip()
                # Clean up the result
                result = result.strip('"\'')
                if result and len(result) >= 3 and len(result) <= 100:
                    return result
        except Exception:
            pass

        # Fallback: extract first word(s) up to numbers/special sequences
        pattern = re.sub(r'[\s#*]+\d+.*$', '', description)
        pattern = re.sub(r'\s+(STORE|BRANCH|LOCATION).*$', '', pattern, flags=re.IGNORECASE)
        if pattern and len(pattern) >= 3:
            return pattern.strip()

        return None

    def categorize_single(self, description: str, categories: list[dict]) -> Optional[int]:
        """Use Ollama to categorize a single transaction.

        Args:
            description: Transaction description
            categories: List of dicts with 'id' and 'name' keys

        Returns:
            Category ID or None if unable to categorize
        """
        cat_list = "\n".join([f"- ID {c['id']}: {c['name']}" for c in categories])

        prompt = f"""You are a financial transaction categorizer. Given a transaction description, return ONLY the category ID number that best matches.

Examples of correct categorizations:
- "WALMART" or "WM SUPERCENTER" → Household > Groceries
- "TOM THUMB", "SPROUTS", "INDIA METRO" → Household > Groceries
- "7-ELEVEN" → Food & Outing (snacks/convenience)
- "STARBUCKS", "KED'S ICE CREAM" → Food & Outing
- "TST*" restaurants → Food & Outing > Eating out
- "ROSS STORES", "DOLLAR TREE", "BATH & BODY" → Shopping/LTE
- "AMAZON" purchases → Shopping/LTE (default)
- "Supercuts" → Beauty > Grooming
- "ISLAMIC ASSOCIATION" → Social work > Charity
- "MASTERKANG" martial arts → Bill Payment > Taekwondo
- "Google One", "YouTube Premium" → Apps
- "EPIC PIZZA" → Food & Outing > Eating out

Categories:
{cat_list}

Transaction: "{description}"

Rules:
- Return ONLY the numeric ID, nothing else
- Choose the most specific subcategory when available
- If unsure, return 0

Category ID:"""

        try:
            resp = requests.post(
                f"{self.url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=30
            )
            if resp.status_code == 200:
                result = resp.json().get("response", "").strip()
                # Extract just the number
                match = re.search(r'\d+', result)
                if match:
                    cat_id = int(match.group())
                    # Verify it's a valid category
                    valid_ids = {c["id"] for c in categories}
                    if cat_id in valid_ids:
                        return cat_id
        except Exception:
            pass

        return None

    def categorize_batch(self, transactions: list[dict], categories: list[dict]) -> list[dict]:
        """Categorize multiple transactions using AI.

        Args:
            transactions: List of transaction dicts with 'description' and 'kind'
            categories: List of category dicts with 'id' and 'name'

        Returns:
            Same transactions list with 'ai_category_id' added where applicable
        """
        for tx in transactions:
            if tx.get("category_id") is None and tx.get("kind") == "expense":
                cat_id = self.categorize_single(tx["description"], categories)
                tx["ai_category_id"] = cat_id

        return transactions
