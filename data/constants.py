import re

from service.FileImporterService import Path

# File upload limits
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_PAGES = 50

# UI
DATE_FORMAT_FILE    = '%d/%m/%Y'
DATE_FORMAT_DISPLAY = 'DD/MM/YYYY'
DATE_FORMAT_TIME    = 'DD/MM/YYYY HH:mm'

AMOUNT_TOLERANCE = 0.011   # cents
MAX_CONTINUATION_LINES = 2

# File parsing
CSV_COLUMNS = ["Date", "BalanceDate", "Description", "Expense", "Income",
               "Accounting Balance", "Balance", "Category"]
SUPPORTED_TYPES = ["csv", "pdf"]
NUMERIC_COLUMNS = ["Expense", "Income", "Accounting Balance", "Balance"]
DEFAULT_CATEGORY = "Others"
DEFAULT_CSV_PATH = Path("data/csv/transactions.csv")

# Classification
MIN_KEY_LENGTH = 4
ML_SUGGESTION_CONFIDENCE = 0.7

_DATE = r"\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2}"
_LINE_RE = re.compile(rf"^\s*({_DATE})(?:\s+({_DATE}))?\s*(.*)$")
# 1.234,56 | 1,234.56 | 1 234,56 | 1234,56 | 25,50 (optional sign, optional trailing '-')
_MONEY_RE = re.compile(r"(?<![\w.,/])[-+]?(?:\d{1,3}(?:[., ]\d{3})+|\d+)[.,]\d{2}-?(?!\w)")

_OPENING_RE = re.compile(r"\b(saldo (anterior|inicial|de abertura)|opening balance|previous balance|balance brought forward)\b")
_CLOSING_RE = re.compile(r"\b(saldo (final|atual|actual|de fecho)|closing balance|new balance)\b")
_BALANCE_LINE_RE = re.compile(r"^(saldo|balance|total|transporte|a transportar)\b")
_HEADER_RE = re.compile(r"\b(saldo|pagina|page|extrato|statement|iban|nib|conta|data|date|descri\w*|debito|credito|total|balance)\b")
_DEBIT_RE = re.compile(r"\b(debito|debit|expense)\b")
_CREDIT_RE = re.compile(r"\b(credito|credit|income)\b")

# First four digits of a Portuguese IBAN after "PT50": the bank code. Verify against your own statements.
_IBAN_BANK_CODES = {
    "0035": "CGD", "0033": "BCP", "0007": "Novo Banco", "0018": "Santander",
    "0010": "BPI", "0036": "Montepio", "0045": "Caixa Agricola",
    "0193": "Banco CTT", "0023": "ActivoBank",
}
_BANK_KEYWORDS: list[tuple[str, re.Pattern]] = [
    ("CGD", re.compile(r"\b(caixa geral de depositos|cgd|caixadirecta)\b")),
    ("BCP", re.compile(r"\b(millennium bcp|millennium|bcp)\b")),
    ("Novo Banco", re.compile(r"\bnovo banco\b")),
    ("Santander", re.compile(r"\bsantander\b")),
    ("BPI", re.compile(r"\b(banco bpi|bpi)\b")),
    ("Caixa Agricola", re.compile(r"\b(caixa agricola|credito agricola)\b")),
    ("Montepio", re.compile(r"\bmontepio\b")),
    ("ActivoBank", re.compile(r"\bactivobank\b")),
]

_STOPWORDS = {
    "compra", "pagamento", "transferencia", "levantamento", "multibanco", "mbway", "debito", "credito",
    "para", "from", "payment", "purchase", "card", "cartao", "conta", "ref", "referencia",
}
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
