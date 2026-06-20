import pdfplumber
import pandas as pd
import re
import json
import os
from datetime import datetime
from typing import Any
from collections import Counter

class BankStatementExtractor:
    """
    Extracts and processes bank statements from PDF files.
    Automatically categorises transactions using keyword matching.

    Category names are aligned with the main app's category system
    (see data/categories.py).
    """

    def __init__(self):
        # Keyword lists per category — aligned with the app's category names
        self.categories: dict[str, list[str]] = {
            "Food": [
                "supermarket", "continente", "pingo doce", "lidl", "aldi", "market",
                "restaurant", "cafe", "bakery", "auchan", "el corte",
                "groceries", "grocery", "deli", "butcher", "fishmonger",
                "froiz", "mercadona", "intermarche",
            ],
            "Transportation": [
                "uber", "bolt", "taxi", "cp", "comboios", "metro", "carris",
                "transport", "gas station", "galp", "bp", "repsol", "prio", "cepsa",
                "parking", "toll", "via verde", "scut",
                "garage", "mechanic", "tires", "service", "maintenance",
            ],
            "Housing": [
                "rent", "condo", "condominium", "electricity", "edp", "endesa",
                "water", "epal", "indaqua", "gas", "meo", "nos",
                "vodafone", "internet", "tv", "telephone", "property tax", "imi",
            ],
            "Healthcare": [
                "pharmacy", "doctor", "appointment", "hospital", "clinic",
                "dentist", "nursing", "exams", "lab", "health insurance",
                "medicare", "advancecare", "multicare",
            ],
            "Education": [
                "school", "university", "college", "tuition", "book", "supplies",
                "course", "training", "workshop", "tutoring", "lessons",
            ],
            "Entertainment": [
                "cinema", "theatre", "concert", "show", "ticket",
                "netflix", "spotify", "disney", "hbo", "amazon prime", "gaming",
                "playstation", "xbox", "steam", "game", "bar",
            ],
            "Personal": [
                "clothing", "shoes", "shirt", "trousers", "dress",
                "zara", "h&m", "bershka", "pull and bear", "mango", "c&a", "primark",
                "fashion", "gym", "haircut", "barber",
            ],
            "Insurance": [
                "insurance", "bank fee", "commission", "lawyer", "accountant",
                "cleaning", "electrician", "plumber",
            ],
            "Debt": [
                "credit card", "loan", "mortgage", "instalment",
            ],
            "Savings": [
                "savings", "deposit", "transfer to savings",
            ],
            "Gifts": [
                "wedding", "birthday", "gift", "souvenir", "toy",
            ],
            "Income": [
                "salary", "wage", "payroll", "transfer in", "refund",
            ],
            "Subscriptions": [
                "spotify", "apple", "netflix", "youtube premium", "amazon prime",
                "disney+", "hbo", "subscription",
            ],
            "Others": [],  # Default / fallback category
        }

        self._expand_categories()

        # Known bank PDF date-format patterns
        self.bank_patterns: dict[str, dict] = {
            "CGD":        {"date_pattern": r"(\d{2}[/-]\d{2}[/-]\d{4})", "encoding": "latin1"},
            "BCP":        {"date_pattern": r"(\d{4}[/-]\d{2}[/-]\d{2})", "encoding": "utf-8"},
            "Novo Banco": {"date_pattern": r"(\d{2}[/-]\d{2}[/-]\d{4})", "encoding": "utf-8"},
            "Santander":  {"date_pattern": r"(\d{2}[/-]\d{2}[/-]\d{4})", "encoding": "latin1"},
            "BPI":        {"date_pattern": r"(\d{2}[/-]\d{2}[/-]\d{4})", "encoding": "utf-8"},
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _expand_categories(self):
        """Add common synonyms/variants to keyword lists."""
        synonyms: dict[str, list[str]] = {
            "Food":           ["food", "meal", "dinner", "lunch", "snack"],
            "Transportation": ["travel", "commute", "journey"],
            "Housing":        ["home", "house", "dwelling"],
            "Entertainment":  ["leisure", "fun", "hobby"],
        }
        for category, extras in synonyms.items():
            if category in self.categories:
                self.categories[category].extend(extras)

    @staticmethod
    def _parse_amount(value_str: str) -> float:
        """Convert a localised number string to float."""
        cleaned = value_str.replace(" ", "").replace(",", ".")
        cleaned = re.sub(r"[^\d.-]", "", cleaned)
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0

    # ------------------------------------------------------------------
    # PDF reading
    # ------------------------------------------------------------------

    def _extract_text(self, pdf_path: str) -> str:
        """Extract raw text from all pages of a PDF."""
        full_text = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception as exc:
            print(f"Error reading PDF: {exc}")
        return full_text

    def _extract_tables(self, pdf_path: str) -> list[pd.DataFrame]:
        """Extract tables directly from a PDF."""
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    for table in page.extract_tables():
                        if table and len(table) > 1:
                            tables.append(pd.DataFrame(table[1:], columns=table[0]))
        except Exception as exc:
            print(f"Error extracting tables: {exc}")
        return tables

    # ------------------------------------------------------------------
    # Bank identification
    # ------------------------------------------------------------------

    def identify_bank(self, text: str) -> str:
        """Identify the bank from statement text."""
        keywords: dict[str, list[str]] = {
            "CGD":        ["caixa geral", "cgd", "caixadirecta"],
            "BCP":        ["millennium", "bcp", "millennium bcp"],
            "Novo Banco": ["novo banco", "nb"],
            "Santander":  ["santander", "santander totta"],
            "BPI":        ["bpi", "banco bpi"],
        }
        text_lower = text.lower()
        for bank, words in keywords.items():
            if any(w in text_lower for w in words):
                return bank
        return "Unknown"

    # ------------------------------------------------------------------
    # Categorisation
    # ------------------------------------------------------------------

    def categorise_transaction(self, description: str) -> dict[str, Any]:
        """
        Score each category against the description and return the best match.

        Returns a dict with keys: category, confidence, keywords.
        """
        desc_lower = description.lower()
        scores: dict[str, dict] = {}

        for category, words in self.categories.items():
            score = 0.0
            matched: list[str] = []
            for word in words:
                if word in desc_lower:
                    # Longer (more specific) keywords score higher
                    score += 1 + len(word) / 10
                    matched.append(word)
            if score > 0:
                scores[category] = {"score": score, "keywords": matched}

        if scores:
            best = max(scores.items(), key=lambda x: x[1]["score"])
            return {
                "category": best[0],
                "confidence": min(1.0, best[1]["score"] / 5),
                "keywords": best[1]["keywords"],
            }

        return {"category": "Others", "confidence": 0.3, "keywords": []}

    def learn_category(self, description: str, correct_category: str):
        """
        Allow manual correction of a category so the extractor improves
        over time within the same session.
        """
        if correct_category not in self.categories:
            self.categories[correct_category] = []

        words = re.findall(r"\b[a-záàâãçéêíóôõúü]{3,}\b", description.lower())
        for word in words:
            if word not in self.categories[correct_category]:
                self.categories[correct_category].append(word)

        print(f"✅ Learned: '{description[:50]}' → {correct_category}")

    # ------------------------------------------------------------------
    # Transaction extraction
    # ------------------------------------------------------------------

    def _extract_transactions_regex(self, text: str) -> list[dict]:
        """Parse transactions from raw text using regex heuristics."""
        transactions: list[dict] = []
        date_pattern = r"(\d{2}[/-]\d{2}[/-]\d{4})"
        amount_pattern = r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"

        for line in text.split("\n"):
            date_match = re.search(date_pattern, line)
            if not date_match:
                continue

            amounts = re.findall(amount_pattern, line)
            description = line[date_match.end():].strip()

            debit = credit = 0.0

            if amounts:
                for amt in amounts:
                    description = description.replace(amt, "").strip()

                if len(amounts) == 1:
                    if re.search(r"\bdebit\b|\bexpense\b|\bdébito\b", line, re.I):
                        debit = self._parse_amount(amounts[0])
                    else:
                        credit = self._parse_amount(amounts[0])
                else:
                    debit = self._parse_amount(amounts[0])
                    credit = self._parse_amount(amounts[1])

            if description and (debit > 0 or credit > 0):
                cat_info = self.categorise_transaction(description)
                transactions.append({
                    "date": date_match.group(1),
                    "description": description,
                    "debit": debit,
                    "credit": credit,
                    "balance": 0.0,
                    "category": cat_info["category"],
                    "category_confidence": cat_info["confidence"],
                    "keywords": cat_info["keywords"],
                })

        return transactions

    def _table_to_transactions(self, df: pd.DataFrame) -> list[dict]:
        """Convert a pdfplumber table DataFrame into a transaction list."""
        transactions: list[dict] = []
        cols = {col.lower(): col for col in df.columns}

        col_date = col_desc = col_debit = col_credit = None

        for col_lower, col_orig in cols.items():
            if any(p in col_lower for p in ("date", "mov", "data")):
                col_date = col_orig
            elif any(p in col_lower for p in ("descri", "description", "text", "movement")):
                col_desc = col_orig
            elif any(p in col_lower for p in ("debit", "expense", "debt")):
                col_debit = col_orig
            elif any(p in col_lower for p in ("credit", "income", "receita")):
                col_credit = col_orig

        if not col_date:
            return transactions

        for _, row in df.iterrows():
            description = str(row[col_desc]) if col_desc and pd.notna(row[col_desc]) else ""
            if not description or description == "nan":
                continue

            cat_info = self.categorise_transaction(description)
            debit = float(row[col_debit]) if col_debit and pd.notna(row[col_debit]) else 0.0
            credit = float(row[col_credit]) if col_credit and pd.notna(row[col_credit]) else 0.0

            if debit > 0 or credit > 0:
                transactions.append({
                    "date": str(row[col_date]) if pd.notna(row[col_date]) else "",
                    "description": description,
                    "debit": debit,
                    "credit": credit,
                    "balance": 0.0,
                    "category": cat_info["category"],
                    "category_confidence": cat_info["confidence"],
                    "keywords": cat_info["keywords"],
                })

        return transactions

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def _category_stats(self, transactions: list[dict]) -> dict[str, dict]:
        """Compute per-category aggregates."""
        stats: dict[str, dict] = {}
        for t in transactions:
            cat = t["category"]
            if cat not in stats:
                stats[cat] = {"total_spent": 0.0, "total_received": 0.0,
                              "num_transactions": 0, "avg_confidence": 0.0}
            stats[cat]["total_spent"] += t["debit"]
            stats[cat]["total_received"] += t["credit"]
            stats[cat]["num_transactions"] += 1
            stats[cat]["avg_confidence"] += t["category_confidence"]

        for cat in stats:
            n = stats[cat]["num_transactions"]
            if n:
                stats[cat]["avg_confidence"] /= n

        return stats

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def process_statement(self, pdf_path: str) -> dict[str, Any]:
        """
        Process a PDF bank statement end-to-end.
        Returns a result dict or a dict with key 'error' on failure.
        """
        print(f"📄 Processing: {pdf_path}")

        text = self._extract_text(pdf_path)
        if not text:
            return {"error": "Could not extract text from PDF."}

        bank = self.identify_bank(text)
        print(f"🏦 Bank identified: {bank}")

        transactions = self._extract_transactions_regex(text)

        if not transactions:
            print("Trying table extraction...")
            tables = self._extract_tables(pdf_path)
            if tables:
                transactions = self._table_to_transactions(tables[0])

        # Compute running balance
        running = 0.0
        for t in transactions:
            running += t["credit"] - t["debit"]
            t["balance"] = running

        return {
            "bank": bank,
            "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_transactions": len(transactions),
            "total_debits": sum(t["debit"] for t in transactions),
            "total_credits": sum(t["credit"] for t in transactions),
            "final_balance": sum(t["credit"] - t["debit"] for t in transactions),
            "category_stats": self._category_stats(transactions),
            "transactions": transactions,
        }

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def export_csv(self, result: dict, output_path: str):
        """Export transactions to CSV."""
        if result.get("transactions"):
            pd.DataFrame(result["transactions"]).to_csv(
                output_path, index=False, encoding="utf-8-sig"
            )
            print(f"✅ CSV exported: {output_path}")
        else:
            print("⚠️ No transactions to export.")

    def export_json(self, result: dict, output_path: str):
        """Export full result to JSON."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"✅ JSON exported: {output_path}")

    def export_excel(self, result: dict, output_path: str):
        """Export result to an Excel workbook with multiple sheets."""
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            if result.get("transactions"):
                pd.DataFrame(result["transactions"]).to_excel(
                    writer, sheet_name="Transactions", index=False
                )

            pd.DataFrame([{
                "Bank": result["bank"],
                "Processed At": result["processed_at"],
                "Total Transactions": result["total_transactions"],
                "Total Debits": result["total_debits"],
                "Total Credits": result["total_credits"],
                "Final Balance": result["final_balance"],
            }]).to_excel(writer, sheet_name="Summary", index=False)

            if result.get("category_stats"):
                (
                    pd.DataFrame(result["category_stats"])
                    .T.reset_index()
                    .rename(columns={"index": "Category"})
                    .to_excel(writer, sheet_name="Stats", index=False)
                )
        print(f"✅ Excel exported: {output_path}")
