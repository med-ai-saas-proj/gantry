from datetime import datetime


def add_current_date():
    return f"Today is: {datetime.today().strftime('%Y-%m-%d')}"
