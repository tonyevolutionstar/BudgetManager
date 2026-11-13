from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime
from typing import Any

import pandas as pd
import pdfplumber
import data.constants as const

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------

def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def _norm(text: Any) -> str:
    """Lowercase, no accents, single spaces."""
    return re.sub(r"\s+", " ", _strip_accents(str(text or "")).lower()).strip()


def _normalise_date(value: str | None) -> str | None:
    """Return DD/MM/YYYY, or None when the text is not a valid date."""
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None


def _parse_amount(token: Any) -> float | None:
    """Parse '1.234,56', '1,234.56', '1 234,56', '-25,50', '25,50-'. None when not a number."""
    if token is None:
        return None
    raw = str(token).strip()
    negative = raw.startswith("-") or raw.endswith("-")
    s = re.sub(r"[^\d.,]", "", raw)
    if not s:
        return None
    idx = max(s.rfind("."), s.rfind(","))
    if idx != -1 and len(s) - idx - 1 == 2:      # last separator followed by 2 digits = decimal separator
        integer, decimals = re.sub(r"[.,]", "", s[:idx]), s[idx + 1:]
        s = f"{integer or '0'}.{decimals}"
    else:
        s = re.sub(r"[.,]", "", s)
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def _keyword_pattern(keyword: str) -> re.Pattern:
    """Word-boundary pattern: short keywords (<=3 chars) must be whole words,
    longer ones may be a word prefix ('mcdonald' matches 'mcdonalds')."""
    body = re.escape(keyword)
    tail = r"(?![a-z0-9])" if len(keyword) <= 3 else ""
    return re.compile(rf"(?<![a-z0-9]){body}{tail}")


def _safe_cell(value: Any) -> Any:
    """Prefix a quote so Excel/LibreOffice do not evaluate text as a formula."""
    if isinstance(value, str) and value.startswith(const._FORMULA_PREFIXES):
        return "'" + value
    return value


def _sanitise_for_export(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "keywords" in df.columns:
        df["keywords"] = df["keywords"].map(lambda k: ", ".join(k) if isinstance(k, list) else k)
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
            df[col] = df[col].map(_safe_cell)
    return df


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------

class BankStatementExtractor:
    """Extracts and categorises transactions from a PDF statement (path or file-like object).

    Category names match the categories in DatabaseSchema.sql.
    """

    def __init__(self):
        # Accent-free, lowercase keywords. Do not list the same keyword in two categories.
        self.categories: dict[str, list[str]] = {
            "Food": [
                "supermercado", "continente", "pingo doce", "lidl", "aldi", "auchan", "el corte", "minipreco",
                "intermarche", "mercadona", "froiz", "restaurante", "restaurant", "cafe", "pastelaria",
                "padaria", "bakery", "talho", "peixaria", "groceries", "grocery", "deli", "butcher",
                "fishmonger", "mcdonald", "burger king", "kfc", "pizza",
            ],
            "Transportation": [
                "uber", "bolt", "taxi", "cp", "comboios", "metro", "carris", "galp", "bp", "repsol", "prio",
                "cepsa", "gasolina", "gasoleo", "combustivel", "estacionamento", "parking", "portagem",
                "toll", "via verde", "scut", "garagem", "garage", "oficina", "mecanico", "mechanic",
                "pneus", "tires",
            ],
            "Housing": [
                "renda", "rent", "condominio", "condominium", "electricity", "edp", "endesa", "agua", "water",
                "epal", "indaqua", "galp gas", "gas natural", "meo", "nos", "vodafone", "nowo", "internet",
                "telefone", "telephone", "imi", "property tax",
            ],
            "Healthcare": [
                "farmacia", "pharmacy", "medico", "doctor", "consulta", "hospital", "clinica", "clinic",
                "dentista", "dentist", "enfermagem", "exames", "multicare", "advancecare", "medicare",
            ],
            "Education": [
                "escola", "school", "universidade", "university", "college", "propina", "tuition", "curso",
                "course", "formacao", "training", "workshop", "explicacoes", "tutoring", "lessons",
            ],
            "Entertainment": [
                "cinema", "teatro", "theatre", "concerto", "concert", "bilhete", "ticket",
                "playstation", "xbox", "steam", "gaming", "bar", "discoteca", "fnac",
            ],
            "Personal": [
                "roupa", "clothing", "sapatos", "shoes", "zara", "h&m", "bershka", "pull and bear", "mango",
                "c&a", "primark", "fashion", "ginasio", "gym", "fitness", "holmes place", "cabeleireiro",
                "haircut", "barber", "barbeiro",
            ],
            "Insurance": [
                "seguro", "insurance", "health insurance", "fidelidade", "allianz", "zurich", "generali",
                "comissao", "commission", "bank fee", "anuidade", "advogado", "lawyer", "contabilista",
                "accountant", "limpeza", "eletricista", "canalizador",
            ],
            "Debt": ["cartao de credito", "credit card", "emprestimo", "loan", "hipoteca", "mortgage", "prestacao", "instalment"],
            "Savings": ["poupanca", "savings", "deposito a prazo", "deposit", "transfer to savings"],
            "Gifts": ["casamento", "wedding", "aniversario", "birthday", "presente", "gift", "souvenir", "brinquedo", "toy"],
            "Income": [
                "salario", "salary", "vencimento", "ordenado", "wage", "payroll", "subsidio", "reembolso",
                "refund", "transferencia recebida", "transfer in",
            ],
            "Subscriptions": [
                "spotify", "netflix", "disney", "hbo", "amazon prime", "youtube premium", "apple.com", "apple",
                "subscription", "subscricao", "assinatura",
            ],
            "Others": [],  # default / fallback
        }
        self._patterns: dict[str, list[tuple[re.Pattern, str]]] | None = None

    # ------------------------------------------------------------------
    # PDF reading
    # ------------------------------------------------------------------

    @staticmethod
    def _open(source):
        if hasattr(source, "seek"):
            source.seek(0)
        return pdfplumber.open(source)

    def _extract_text(self, source) -> str:
        """Raw text of the first MAX_PAGES pages ('' on failure)."""
        parts: list[str] = []
        try:
            with self._open(source) as pdf:
                for page in pdf.pages[:const.MAX_PAGES]:
                    text = page.extract_text()
                    if text:
                        parts.append(text)
        except Exception:
            logger.exception("Error reading PDF")
            return ""
        return "\n".join(parts)

    def _extract_tables(self, source) -> list[pd.DataFrame]:
        """Tables found in the PDF, with unique non-null column names."""
        tables: list[pd.DataFrame] = []
        try:
            with self._open(source) as pdf:
                for page in pdf.pages[:const.MAX_PAGES]:
                    for table in page.extract_tables():
                        if not table or len(table) < 2:
                            continue
                        headers, seen = [], {}
                        for cell in table[0]:
                            name = str(cell).strip() if cell is not None else ""
                            seen[name] = seen.get(name, 0) + 1
                            headers.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
                        tables.append(pd.DataFrame(table[1:], columns=headers))
        except Exception:
            logger.exception("Error extracting tables")
        return tables

    # ------------------------------------------------------------------
    # Bank identification
    # ------------------------------------------------------------------

    def identify_bank(self, text: str) -> str:
        """Identify the bank: IBAN bank code first, then names found in the page header."""
        match = re.search(r"\bPT\s?\d{2}\s?(\d{4})", text.upper())
        if match and match.group(1) in const._IBAN_BANK_CODES:
            return const._IBAN_BANK_CODES[match.group(1)]

        header = _norm(text[:1500])  # counterparties further down must not decide the bank
        for bank, pattern in const._BANK_KEYWORDS:
            if pattern.search(header):
                return bank
        return "Unknown"

    # ------------------------------------------------------------------
    # Categorisation
    # ------------------------------------------------------------------

    def _compiled_patterns(self) -> dict[str, list[tuple[re.Pattern, str]]]:
        if self._patterns is None:
            self._patterns = {
                category: [(_keyword_pattern(_norm(w)), _norm(w)) for w in words if _norm(w)]
                for category, words in self.categories.items()
            }
        return self._patterns

    def categorise_transaction(self, description: str) -> dict[str, Any]:
        """Score each category against the description and return the best match.

        Returns a dict with keys: category, confidence, keywords.
        """
        desc = _norm(description)
        best: tuple[str, float, list[str]] | None = None

        for category, patterns in self._compiled_patterns().items():
            score, matched = 0.0, []
            for pattern, word in patterns:
                if pattern.search(desc):
                    score += 1 + len(word) / 10   # longer (more specific) keywords score higher
                    matched.append(word)
            if score > 0 and (best is None or score > best[1]):
                best = (category, score, matched)

        if best:
            return {"category": best[0], "confidence": min(1.0, best[1] / 5), "keywords": best[2]}
        return {"category": "Others", "confidence": 0.3, "keywords": []}

    def learn_category(self, description: str, correct_category: str) -> None:
        """Teach the extractor from a manual correction (this session only).

        Only meaningful words are added (>= 4 letters, not generic stop words).
        """
        self.categories.setdefault(correct_category, [])
        for word in re.findall(r"[a-z]{4,}", _norm(description)):
            if word not in const._STOPWORDS and word not in self.categories[correct_category]:
                self.categories[correct_category].append(word)
        self._patterns = None
        logger.info("Learned a correction for category '%s'.", correct_category)

    # ------------------------------------------------------------------
    # Text parsing
    # ------------------------------------------------------------------

    def _parse_rest(self, rest: str) -> dict | None:
        """Parse what follows the date(s): description, amount(s) and balance."""
        values: list[tuple[float, str]] = []
        spans: list[tuple[int, int]] = []
        for m in const._MONEY_RE.finditer(rest):
            amount = _parse_amount(m.group(0))
            if amount is not None:
                values.append((amount, m.group(0)))
                spans.append(m.span())
        if not values:
            return None

        description, last = "", 0
        for start, end in spans:
            description += rest[last:start]
            last = end
        description = re.sub(r"\s+", " ", description + rest[last:]).strip(" -;,")
        if not description:
            return None

        first_token = values[0][1]
        marker = -1 if first_token.startswith("-") or first_token.endswith("-") else (1 if first_token.startswith("+") else None)
        if marker is None:
            norm_rest = _norm(rest)
            marker = -1 if const._DEBIT_RE.search(norm_rest) else (1 if const._CREDIT_RE.search(norm_rest) else None)

        nums = [v for v, _ in values]
        row: dict[str, Any] = {
            "description": description, "balance": None, "amount": None,
            "debit": 0.0, "credit": 0.0, "sign": marker,
            "sign_source": "marker" if marker is not None else None, "cont": 0,
        }
        if len(nums) == 1:                         # amount only
            row["amount"] = abs(nums[0])
        elif len(nums) == 2:                       # amount, balance
            row["amount"], row["balance"] = abs(nums[0]), nums[1]
        else:                                      # debit, credit, ..., balance
            debit, credit = abs(nums[0]), abs(nums[1])
            row["balance"] = nums[-1]
            row["debit"], row["credit"] = debit, credit
            row["amount"] = abs(credit - debit) if debit and credit else (debit or credit)
            row["sign"] = 0 if (debit and credit) else (1 if credit else -1)
            row["sign_source"] = "columns"
        return row

    @staticmethod
    def _is_continuation(line: str) -> bool:
        stripped = line.strip()
        return (
            0 < len(stripped) <= 60
            and not const._MONEY_RE.search(stripped)
            and not const._HEADER_RE.search(_norm(stripped))
            and not stripped.isdigit()
        )

    def _parse_text(self, text: str) -> tuple[list[dict], float | None, float | None]:
        """Return (rows, opening_balance, closing_balance)."""
        rows: list[dict] = []
        opening = closing = None
        last_was_row = False

        for line in text.split("\n"):
            norm_line = _norm(line)
            money = const._MONEY_RE.findall(line)

            if money and const._OPENING_RE.search(norm_line):
                opening = _parse_amount(money[-1])
                last_was_row = False
                continue
            if money and const._CLOSING_RE.search(norm_line):
                closing = _parse_amount(money[-1])
                last_was_row = False
                continue

            match = const._LINE_RE.match(line)
            if not match:
                if last_was_row and rows and rows[-1]["cont"] < const.MAX_CONTINUATION_LINES and self._is_continuation(line):
                    rows[-1]["description"] += " " + line.strip()
                    rows[-1]["cont"] += 1
                else:
                    last_was_row = False
                continue

            last_was_row = False
            date = _normalise_date(match.group(1))
            if date is None:
                continue
            rest = match.group(3)
            if const._BALANCE_LINE_RE.match(_norm(rest)):
                continue
            row = self._parse_rest(rest)
            if row is None:
                continue
            row["date"] = date
            row["value_date"] = _normalise_date(match.group(2)) or date
            rows.append(row)
            last_was_row = True

        return rows, opening, closing

    # ------------------------------------------------------------------
    # Sign resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_order(rows: list[dict], opening: float | None) -> str | None:
        """'asc' (oldest first) or 'desc', judged by which one the balances support."""
        asc = desc = 0
        for prev, cur in zip(rows, rows[1:]):
            if prev["balance"] is None or cur["balance"] is None:
                continue
            diff = abs(cur["balance"] - prev["balance"])
            if cur["amount"] is not None and abs(diff - cur["amount"]) <= const.AMOUNT_TOLERANCE:
                asc += 1
            if prev["amount"] is not None and abs(diff - prev["amount"]) <= const.AMOUNT_TOLERANCE:
                desc += 1
        if opening is not None and rows:
            first, last = rows[0], rows[-1]
            if first["balance"] is not None and first["amount"] is not None \
                    and abs(abs(first["balance"] - opening) - first["amount"]) <= const.AMOUNT_TOLERANCE:
                asc += 1
            if last["balance"] is not None and last["amount"] is not None \
                    and abs(abs(last["balance"] - opening) - last["amount"]) <= const.AMOUNT_TOLERANCE:
                desc += 1
        if asc == desc == 0:
            return None
        return "asc" if asc >= desc else "desc"

    @staticmethod
    def _resolve_signs(rows: list[dict], opening: float | None, order: str | None) -> None:
        """Fill row['sign'] from the balance before each row (the next row when newest-first)."""
        last = len(rows) - 1
        for i, row in enumerate(rows):
            if row["sign"] is not None or row["amount"] is None or row["balance"] is None:
                continue
            if order == "asc":
                before = rows[i - 1]["balance"] if i > 0 else opening
            elif order == "desc":
                before = rows[i + 1]["balance"] if i < last else opening
            else:
                before = None
            if before is None:
                continue
            delta = row["balance"] - before
            if delta != 0 and abs(abs(delta) - row["amount"]) <= const.AMOUNT_TOLERANCE:
                row["sign"] = 1 if delta > 0 else -1
                row["sign_source"] = "balance"

    def _build_transactions(self, rows: list[dict], opening: float | None, order: str | None) -> list[dict]:
        self._resolve_signs(rows, opening, order)
        transactions: list[dict] = []
        for row in rows:
            cat = self.categorise_transaction(row["description"])
            sign, source = row["sign"], row["sign_source"]
            if sign is None:                       # last resort: guess, and flag it for review
                sign = 1 if cat["category"] == "Income" else -1
                source = "assumed"
            if sign == 0:                          # explicit debit and credit columns
                debit, credit = row["debit"], row["credit"]
            else:
                debit = row["amount"] if sign < 0 else 0.0
                credit = row["amount"] if sign > 0 else 0.0
            transactions.append({
                "date": row["date"],
                "value_date": row["value_date"],
                "description": row["description"],
                "debit": debit,
                "credit": credit,
                "balance": row["balance"],
                "category": cat["category"],
                "category_confidence": cat["confidence"],
                "keywords": cat["keywords"],
                "sign_source": source,
            })
        return transactions

    # ------------------------------------------------------------------
    # Table fallback
    # ------------------------------------------------------------------

    def _table_to_transactions(self, df: pd.DataFrame) -> list[dict]:
        """Convert a pdfplumber table into transactions (headers matched ignoring accents/case)."""
        headers = [_norm(c) for c in df.columns]
        idx: dict[str, int] = {}
        for i, h in enumerate(headers):
            if "data" in h or "date" in h:
                idx.setdefault("date", i)        # the first date column is the operation date
            elif any(k in h for k in ("descri", "movimento", "text", "detalhe")):
                idx.setdefault("desc", i)
            elif any(k in h for k in ("debito", "debit", "expense", "saida", "despesa")):
                idx.setdefault("debit", i)
            elif any(k in h for k in ("credito", "credit", "income", "receita", "entrada")):
                idx.setdefault("credit", i)
            elif any(k in h for k in ("saldo", "balance")):
                idx.setdefault("balance", i)
            elif any(k in h for k in ("valor", "montante", "amount")):
                idx.setdefault("amount", i)

        if "date" not in idx or "desc" not in idx or not ({"debit", "credit", "amount"} & idx.keys()):
            return []

        def cell(row: pd.Series, key: str) -> float | None:
            return _parse_amount(row.iloc[idx[key]]) if key in idx else None

        transactions: list[dict] = []
        for _, row in df.iterrows():
            date = _normalise_date(str(row.iloc[idx["date"]] or "").strip())
            description = re.sub(r"\s+", " ", str(row.iloc[idx["desc"]] or "")).strip()
            if not date or not description:
                continue

            debit = abs(cell(row, "debit") or 0.0)
            credit = abs(cell(row, "credit") or 0.0)
            signed = cell(row, "amount")
            if signed is not None and not (debit or credit):
                debit, credit = (0.0, signed) if signed > 0 else (-signed, 0.0)
            if not (debit or credit):
                continue

            cat = self.categorise_transaction(description)
            transactions.append({
                "date": date, "value_date": date, "description": description,
                "debit": debit, "credit": credit, "balance": cell(row, "balance"),
                "category": cat["category"], "category_confidence": cat["confidence"],
                "keywords": cat["keywords"], "sign_source": "columns",
            })
        return transactions

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    @staticmethod
    def _category_stats(transactions: list[dict]) -> dict[str, dict[str, float]]:
        stats: dict[str, dict[str, float]] = {}
        for t in transactions:
            entry = stats.setdefault(t["category"], {"count": 0, "debits": 0.0, "credits": 0.0})
            entry["count"] += 1
            entry["debits"] = round(entry["debits"] + t["debit"], 2)
            entry["credits"] = round(entry["credits"] + t["credit"], 2)
        return stats

    def process_statement(self, pdf_path) -> dict[str, Any]:
        """Process a PDF statement (file path or file-like object) end to end.

        Returns a result dict, or {'error': message} on failure. Besides the
        transactions, the result reports balance_source ('statement' | 'computed'),
        reconciled (opening + movements == closing, or None) and needs_review
        (number of rows whose sign had to be assumed).
        """
        logger.info("Processing statement")

        text = self._extract_text(pdf_path)
        if not text.strip():
            return {"error": "Could not extract text from the PDF (scanned PDFs are not supported)."}

        bank = self.identify_bank(text)
        rows, opening, closing = self._parse_text(text)
        order = self._detect_order(rows, opening) if rows else None
        transactions = self._build_transactions(rows, opening, order) if rows else []

        if not transactions:
            for table in self._extract_tables(pdf_path):
                transactions.extend(self._table_to_transactions(table))
            order = None

        net_change = round(sum(t["credit"] - t["debit"] for t in transactions), 2)

        if transactions and all(t["balance"] is not None for t in transactions):
            balance_source = "statement"
            if order == "asc":
                final_balance = transactions[-1]["balance"]
            elif order == "desc":
                final_balance = transactions[0]["balance"]
            else:
                final_balance = closing if closing is not None else net_change
        else:
            balance_source = "computed"                # running total of the imported rows, starting at 0
            running = 0.0
            for t in transactions:
                running += t["credit"] - t["debit"]
                t["balance"] = round(running, 2)
            final_balance = net_change

        reconciled = None
        if opening is not None and closing is not None and transactions:
            reconciled = abs(opening + net_change - closing) <= 0.02

        return {
            "bank": bank,
            "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_transactions": len(transactions),
            "total_debits": round(sum(t["debit"] for t in transactions), 2),
            "total_credits": round(sum(t["credit"] for t in transactions), 2),
            "net_change": net_change,
            "final_balance": final_balance,
            "balance_source": balance_source,
            "reconciled": reconciled,
            "needs_review": sum(1 for t in transactions if t["sign_source"] == "assumed"),
            "category_stats": self._category_stats(transactions),
            "transactions": transactions,
        }

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def export_csv(self, result: dict, output_path: str) -> None:
        """Export transactions to CSV (formula-injection safe)."""
        if result.get("transactions"):
            _sanitise_for_export(pd.DataFrame(result["transactions"])).to_csv(
                output_path, index=False, encoding="utf-8-sig"
            )
            logger.info("CSV exported: %s", output_path)
        else:
            logger.warning("No transactions to export.")

    def export_json(self, result: dict, output_path: str) -> None:
        """Export the full result to JSON."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        logger.info("JSON exported: %s", output_path)

    def export_excel(self, result: dict, output_path: str) -> None:
        """Export to an Excel workbook with Transactions / Summary / Stats sheets (formula-injection safe)."""
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            if result.get("transactions"):
                _sanitise_for_export(pd.DataFrame(result["transactions"])).to_excel(
                    writer, sheet_name="Transactions", index=False
                )

            _sanitise_for_export(pd.DataFrame([{
                "Bank": result["bank"],
                "Processed At": result["processed_at"],
                "Total Transactions": result["total_transactions"],
                "Total Debits": result["total_debits"],
                "Total Credits": result["total_credits"],
                "Net Change": result["net_change"],
                "Final Balance": result["final_balance"],
                "Balance Source": result["balance_source"],
            }])).to_excel(writer, sheet_name="Summary", index=False)

            if result.get("category_stats"):
                (
                    _sanitise_for_export(
                        pd.DataFrame(result["category_stats"]).T.reset_index().rename(columns={"index": "Category"})
                    ).to_excel(writer, sheet_name="Stats", index=False)
                )
        logger.info("Excel exported: %s", output_path)