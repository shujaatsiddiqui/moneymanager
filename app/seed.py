"""Initial accounts and categories, copied from the existing Money Manager app."""
from sqlalchemy import select

from .models import USER_ID, Account, Category

# (name, group, is_liability, include_in_totals, is_business)
ACCOUNTS = [
    ("Cash", "Cash", False, True, False),
    ("BOFA", "Accounts", False, True, False),
    ("Chase Checking", "Accounts", False, True, False),
    ("Stock", "Accounts", False, True, False),
    ("Pakistan Account", "Accounts", False, False, False),  # greyed out in your app
    ("Acct Receivable", "Accounts", False, True, False),
    ("Acct Payable", "Accounts", False, True, False),
    ("Chase Business", "Accounts", False, True, True),
    ("BOFA CC", "Card", True, True, False),
    ("Apple Card", "Card", True, True, False),
    ("Amazon", "Card", True, True, False),
    ("Chase CC", "Card", True, True, False),
    ("Chase Savings", "Savings", False, True, False),
]

# (emoji, name, [subcategories], exclude_from_budget)
CATEGORIES = [
    # Income categories for P&L reporting
    ("💰", "Income", ["Salary", "Bonus", "Interest/Dividends", "Freelance", "Gifts", "Other Income"], False),
    # Expense categories
    ("🍜", "Food & Outing", ["Lunch", "Dinner", "Eating out", "Beverages"], False),
    ("👫", "Social Life", ["Friend", "Fellowship", "Alumni", "Dues"], False),
    ("🐶", "Pets", [], False),
    ("🚕", "Transport", ["Bus", "Subway", "Taxi", "Car", "Car lease", "Fuel", "Toll",
                        "Carwash", "Parking", "Registration"], False),
    ("🖼️", "Culture", ["Books", "Movie", "Music", "Apps"], False),
    ("🪑", "Household", ["Appliances", "Furniture", "Kitchen", "Toiletries", "Chandlery",
                        "Groceries"], False),
    ("🧥", "Apparel", ["Clothing", "Fashion", "Shoes", "Laundry"], False),
    # Your screenshot truncates the 5th item ("Gro..." / "Acade..."); edit these if wrong.
    ("💄", "Beauty", ["Cosmetics", "Makeup", "Accessories", "Beauty", "Grooming"], False),
    ("🧘", "Health", ["Health", "Yoga", "Hospital", "Medicine", "OPD", "Dental"], False),
    ("📙", "Education", ["Schooling", "Textbooks", "School supplies", "Academy"], False),
    ("🎁", "Gift", [], False),
    ("", "Other", [], False),
    ("", "Bill Payment", [
        "My iPhone payment", "House rent", "Gas", "Electric", "Tmobile prepaid",
        "Samra Quran", "Furniture", "Jiya airpods", "Rayyan day care", "Internet",
        "Chase card annual payment", "Rayyan Swimming", "Chase CC annual charges",
        "Cvs Extra Care", "Rayyan Quran Course", "Income Tax Payment",
        "Costco Annual Charges", "OTF membership", "Samra Driving Class",
        "Go Daddy Subscription", "Rayyan Islamic School", "Taekwondo", "Garage Rent"], False),
    ("", "Insurance", ["Car", "Medical", "Rent"], False),
    ("", "Shopping/LTE", [], False),
    ("", "Social work", ["Darul uloom fund", "Uzma khala", "Ammi", "Saba Khala",
                         "School Trust", "Sadqa", "Charity", "Zakat"], False),
    ("", "Wife Pocket Money", [], False),
    ("", "Occasional", ["EIDI"], False),
    ("", "Immigiration", ["GC"], False),
    ("", "Non Budget", [], True),
    ("", "Outdoor Sports", ["Swimming"], False),
    ("", "Business Investment", [], True),
    ("", "Loan", [], True),
    ("", "Apps", [
        "Kiddopia", "YouTube", "Amazon Prime", "LinkedIn", "Azure", "Apple Storage",
        "Willow", "Audible", "Google Storage", "One Drive Storage", "Chatgpt",
        "Google One", "Apple Fitness App", "Median Dict", "Claude", "office365",
        "FuboTv", "Apple News", "Google One Samra", "Walmart+"], False),
    ("", "Pakistan Travel Expense", ["Airline tickets", "Gifts"], False),
    ("", "Loan Payment for others", [], False),
    ("", "Startup Investment", [], False),
    ("", "Extra", [], False),
    ("", "LLC", ["Salary", "Laptop Payment"], True),
    ("", "Haj 2026", [], False),
    ("", "Dawat", [], False),
    ("", "Fixed Cost", [], False),
    ("", "Income Tax", [], True),
]


def seed(db) -> None:
    if db.scalars(select(Account).limit(1)).first() is None:
        for i, (name, group, liab, incl, biz) in enumerate(ACCOUNTS):
            db.add(Account(user_id=USER_ID, name=name, group_name=group, is_liability=liab,
                           include_in_totals=incl, is_business=biz, sort=i))
    if db.scalars(select(Category).limit(1)).first() is None:
        for i, (emoji, name, subs, excl) in enumerate(CATEGORIES):
            parent = Category(user_id=USER_ID, name=name, emoji=emoji,
                              exclude_from_budget=excl, sort=i)
            db.add(parent)
            db.flush()
            for j, sub in enumerate(subs):
                db.add(Category(user_id=USER_ID, name=sub, parent_id=parent.id, sort=j))
    db.commit()
