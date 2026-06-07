from datetime import datetime

DATE_FORMATS = {
    "file": "%d/%m/%Y",
    "input": "DD/MM/YYYY",
    "today": ""
}

def get_actual_date():
    return datetime.now()

def format_date(date):
    return date.strftime("%d/%m/%Y")
