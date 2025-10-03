# calculators.py

def calculate_deductions(deductions: dict, age: int) -> int:
    total = 0
    # 80C (max 1,50,000)
    total += min(deductions.get("80C", 0), 150000)
    # NPS 80CCD(1B) (max 50,000)
    total += min(deductions.get("nps", 0), 50000)
    # Health insurance 80D (25k < 60yrs, else 50k)
    max_health = 50000 if age >= 60 else 25000
    total += min(deductions.get("health", 0), max_health)
    return total

# calculators.py

def resident_tax_old(gross_income: int, age: int) -> int:
    tax = 0
    # Define slabs based on age
    if age < 60:
        slabs = [(250000, 0.05), (500000, 0.2), (1000000, 0.3)]
    elif 60 <= age < 80:
        slabs = [(300000, 0.05), (500000, 0.2), (1000000, 0.3)]
    else:
        slabs = [(500000, 0.2), (1000000, 0.3)]

    last_limit = 0
    for limit, rate in slabs:
        if gross_income > limit:
            tax += (limit - last_limit) * rate
            last_limit = limit
        else:
            tax += (gross_income - last_limit) * rate
            last_limit = gross_income
            break

    # Apply top slab if income exceeds highest slab
    if gross_income > last_limit:
        tax += (gross_income - last_limit) * slabs[-1][1]

    return int(tax)


def resident_tax_new(gross_income: int) -> int:
    tax = 0
    # New regime slabs (no deductions considered)
    slabs = [(300000, 0.05), (600000, 0.1), (900000, 0.15), (1200000, 0.2), (1500000, 0.3)]
    last_limit = 0
    for limit, rate in slabs:
        if gross_income > limit:
            tax += (limit - last_limit) * rate
            last_limit = limit
        else:
            tax += (gross_income - last_limit) * rate
            last_limit = gross_income
            break

    # Apply top slab if income exceeds highest slab
    if gross_income > last_limit:
        tax += (gross_income - last_limit) * slabs[-1][1]

    return int(tax)

def nri_tax(gross_income: int) -> int:
    tax = 0
    slabs = [(250000, 0.05), (500000, 0.2), (1000000, 0.3)]
    last_limit = 0
    for limit, rate in slabs:
        if gross_income > limit:
            tax += (min(gross_income, limit) - last_limit) * rate
            last_limit = limit
        else:
            tax += (gross_income - last_limit) * rate
            return int(tax)
    if gross_income > last_limit:
        tax += (gross_income - last_limit) * slabs[-1][1]
    return int(tax)


def huf_tax(gross_income: int) -> int:
    return resident_tax_old(gross_income, 30)


def apply_surcharge(tax: int, income: int) -> int:
    surcharge = 0
    if income > 5000000 and income <= 10000000:
        surcharge = tax * 0.1
    elif income > 10000000 and income <= 20000000:
        surcharge = tax * 0.15
    elif income > 20000000 and income <= 50000000:
        surcharge = tax * 0.25
    elif income > 50000000:
        surcharge = tax * 0.37
    return int(tax + surcharge)


def apply_cess(tax: int) -> int:
    return int(tax * 1.04)


def suggest_itr_form(taxpayer_type: str, has_business: bool, presumptive: bool, special_income: bool) -> str:
    if taxpayer_type == "resident":
        if presumptive:
            return "ITR-4 Sugam"
        elif has_business:
            return "ITR-3"
        elif special_income:
            return "ITR-2"
        else:
            return "ITR-1 Sahaj"
    elif taxpayer_type in ["senior", "nri", "huf"]:
        return "ITR-2"
    return "ITR-1 Sahaj"
