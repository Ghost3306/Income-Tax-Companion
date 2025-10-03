# from django.shortcuts import render
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# import json
# from tax_calculate.models import TaxCalculation
# from users.models import UserAccount
# import numpy as np

# from tax_calculate.models import TaxCalculation

# def get_comparison_graph_data(
#     user_input: dict
# ):
#     """
#     Compare user input tax calculation with historical data for plotting.

#     :param user_input: dict containing keys:
#         - username (optional)
#         - gross_income
#         - taxpayer_type (optional)
#         - regime (optional)
#     :return: dict with two lists:
#         - 'historical': list of historical data from DB
#         - 'user_input': list with single dict for current input
#     """
    
#     gross_income = user_input.get("gross_income")
#     taxpayer_type = user_input.get("taxpayer_type")
#     regime = user_input.get("regime")

#     # Fetch historical data
#     queryset = TaxCalculation.objects.all()
#     if taxpayer_type:
#         queryset = queryset.filter(taxpayer_type=taxpayer_type)
#     if regime:
#         queryset = queryset.filter(regime=regime)

#     queryset = queryset.order_by("gross_income")

#     historical_data = [
#         {
#             "gross_income": item.gross_income,
#             "taxable_income": item.taxable_income,
#             "total_tax": item.total_tax,
#             "created_at": item.created_at.isoformat(),
#         }
#         for item in queryset
#     ]

#     # User input data for comparison
#     user_data = {
#         "gross_income": gross_income,
#         "taxable_income": user_input.get("taxable_income"),
#         "total_tax": user_input.get("total_tax"),
#         "total_tax_new":user_input.get("total_tax_new"),
#         "total_tax_old":user_input.get("total_tax_old"),
#         "created_at": "current_input",
#     }

#     return {
#         "historical": historical_data,
#         "user_input": [user_data]
#     }

# from .calculators import (
#     calculate_deductions,
#     resident_tax_old,
#     resident_tax_new,
#     nri_tax,
#     huf_tax,
#     apply_surcharge,
#     apply_cess,
#     suggest_itr_form,
# )
# from django.contrib.auth import get_user_model
# @csrf_exempt
# def tax_calculator_view(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "POST method required"}, status=400)
    
#     try:
#         data = json.loads(request.body) 
#         user_email = data.get("email") 
#         names = json.loads(user_email) 
#         username = names.get("username")
        
#         # -------------------------------
#         # User handling
#         # -------------------------------
#         user = None
#         if username:
#             user = UserAccount.objects.filter(email=username).first()

#         # -------------------------------
#         # Extract tax details
#         # -------------------------------
#         taxpayer_type = data.get("taxpayer_type", "resident")
#         gross_income = float(data.get("gross_income", 0))
#         age = int(data.get("age", 30))
#         tds = float(data.get("tds", 0))
#         deductions = data.get("deductions", {})
#         has_business = data.get("has_business", False)
#         presumptive = data.get("presumptive", False)
#         special_income = data.get("special_income", False)

#         # -------------------------------
#         # Outlier Removal
#         # -------------------------------
#         all_numeric = [gross_income] + [float(v) for v in deductions.values()]
#         mean = np.mean(all_numeric)
#         std = np.std(all_numeric)

#         def remove_outlier(x):
#             return x if std == 0 or abs(x - mean)/std < 3 else mean

#         gross_income = remove_outlier(gross_income)
#         deductions = {k: remove_outlier(float(v)) for k, v in deductions.items()}

#         # -------------------------------
#         # Deductions & Taxable Income
#         # -------------------------------
#         total_deductions = calculate_deductions(deductions, age)
#         taxable_income = max(0, gross_income - total_deductions)

#         # -------------------------------
#         # Calculate both old and new regime taxes
#         # -------------------------------
#         if taxpayer_type == "resident":
#             tax_old = resident_tax_old(taxable_income, age)
#             tax_new = resident_tax_new(gross_income)  # New regime ignores deductions
#         elif taxpayer_type == "senior":
#             tax_old = resident_tax_old(taxable_income, age)
#             tax_new = resident_tax_new(gross_income)
#         elif taxpayer_type == "nri":
#             tax_old = nri_tax(taxable_income)
#             tax_new = nri_tax(gross_income)
#         elif taxpayer_type == "huf":
#             tax_old = huf_tax(taxable_income)
#             tax_new = huf_tax(gross_income)
#         else:
#             tax_old = resident_tax_old(taxable_income, age)
#             tax_new = resident_tax_new(gross_income)

#         tax_old = apply_surcharge(tax_old, taxable_income)
#         tax_old = apply_cess(tax_old)

#         tax_new = apply_surcharge(tax_new, gross_income)
#         tax_new = apply_cess(tax_new)

#         # -------------------------------
#         # Refund or payable
#         # -------------------------------
#         result_data = {}
#         if tds > tax_old:
#             result_data["refund_old"] = tds - tax_old
#         elif tax_old > tds:
#             result_data["payable_old"] = tax_old - tds
#         else:
#             result_data["message_old"] = "No refund or payable"

#         if tds > tax_new:
#             result_data["refund_new"] = tds - tax_new
#         elif tax_new > tds:
#             result_data["payable_new"] = tax_new - tds
#         else:
#             result_data["message_new"] = "No refund or payable"

#         # -------------------------------
#         # Prepare comparison data
#         # -------------------------------
#         user_input = {
#             "gross_income": gross_income,
#             "taxable_income": taxable_income,
#             "total_tax_old": tax_old,
#             "total_tax_new": tax_new,
#             "taxpayer_type": taxpayer_type
#         }
#         print(tax_new,tax_old)
#         comparison_data = get_comparison_graph_data(user_input)

#         # -------------------------------
#         # Final response
#         # -------------------------------
#         result_data.update({
#             "gross_income": gross_income,
#             "deductions": total_deductions,
#             "taxable_income": taxable_income,
#             "total_tax_old": tax_old,
#             "total_tax_new": tax_new,
#             "itr_form": suggest_itr_form(taxpayer_type, has_business, presumptive, special_income),
#             "comparison_graph": comparison_data
#         })

#         # -------------------------------
#         # Save calculation to DB
#         # -------------------------------
#         tax_record = TaxCalculation(
#             user=username,
#             taxpayer_type=taxpayer_type,
#             regime="both",
#             gross_income=gross_income,
#             age=age,
#             tds=tds,
#             deductions=deductions,
#             has_business=has_business,
#             presumptive=presumptive,
#             special_income=special_income,
#             taxable_income=taxable_income,
#             total_tax=max(tax_old, tax_new),
#             result=result_data
#         )

#         try:
#             tax_record.save()
#         except Exception as e:
#             print(e)

#         return JsonResponse(result_data)
    
#     except Exception as e:
#         print(e)
#         return JsonResponse({"error": str(e)}, status=500)

# @csrf_exempt
# def tax_history_api(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "POST method required"}, status=400)

#     try:
#         # Parse JSON body once
#         data = json.loads(request.body)
#         username = data.get("username")  # directly get from dict

#         if not username:
#             return JsonResponse({"error": "Username is required"}, status=400)

#         # Fetch user instance
#         user = UserAccount.objects.filter(username=username).first()
#         if not user:
#             return JsonResponse({"error": "User not found"}, status=404)

#         # Fetch tax calculation history for this user
#         history = TaxCalculation.objects.filter(user=user).order_by('-created_at')

#         # Serialize data
#         history_data = [
#             {
#                 "id": item.id,
#                 "gross_income": item.gross_income,
#                 "taxable_income": item.taxable_income,
#                 "total_tax": item.total_tax,
#                 "created_at": item.created_at.isoformat(),
#             }
#             for item in history
#         ]

#         return JsonResponse(history_data, safe=False)

#     except Exception as e:
#         print(e)
#         return JsonResponse({"error": str(e)}, status=500)
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import numpy as np
from tax_calculate.models import TaxCalculation
from users.models import UserAccount

from .calculators import (
    calculate_deductions,
    resident_tax_old,
    resident_tax_new,
    nri_tax,
    huf_tax,
    apply_surcharge,
    apply_cess,
    suggest_itr_form,
)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path
import tempfile
import re
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import numpy as np
import cv2
# ================== REGEX & HELPERS ==================
PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
TAN_REGEX = re.compile(r"\b[A-Z]{4}[0-9]{5}[A-Z]\b")
AY_REGEX = re.compile(r"Assessment Year\s*:? ([0-9]{4}\s*-\s*[0-9]{2,4})", re.I)
AMOUNT_REGEX = re.compile(r"([0-9,]+\.\d{2}|[0-9,]+)")

def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def extract_text(path: Path) -> str:
    try:
        with pdfplumber.open(str(path)) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    except:
        return ""

def ocr_text(path: Path) -> str:
    images = convert_from_path(str(path), dpi=300)
    texts = []
    for img in images:
        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
        thr = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        pil = Image.fromarray(thr)
        texts.append(pytesseract.image_to_string(pil))
    return "\n".join(texts)

def parse_fields(text: str) -> dict:
    fields = {
        "employee_name": None,
        "PAN_employee": None,
        "employer_name": None,
        "PAN_employer": None,
        "TAN_employer": None,
        "assessment_year": None,
        "period_from": None,
        "period_to": None,
        "gross_salary": None,
        "total_exemptions": None,
        "standard_deduction": None,
        "professional_tax": None,
        "total_deductions_chapter_VIA": None,
        "total_taxable_income": None,
        "tax_on_income": None,
        "rebate_87A": None,
        "health_education_cess": None,
        "relief_89": None,
        "net_tax_payable": None,
        "tax_deducted": None,
        "tax_deposited": None,
    }

    lines = [normalize_spaces(l) for l in text.splitlines() if l.strip()]

    # Employer & Employee
    emp = re.search(r"Name and address of the Employer.*?\n(.+)", text, re.I)
    if emp: fields["employer_name"] = normalize_spaces(emp.group(1))
    emp2 = re.search(r"Name and address of the Employee.*?\n(.+)", text, re.I)
    if emp2: fields["employee_name"] = normalize_spaces(emp2.group(1))

    for l in lines:
        if "PAN of the Employee" in l:
            m = PAN_REGEX.search(l)
            if m: fields["PAN_employee"] = m.group(0)
        if "PAN of the Deductor" in l:
            m = PAN_REGEX.search(l)
            if m: fields["PAN_employer"] = m.group(0)
        if "TAN of the Deductor" in l:
            m = TAN_REGEX.search(l)
            if m: fields["TAN_employer"] = m.group(0)

    # Assessment Year
    ay = AY_REGEX.search(text)
    if ay: fields["assessment_year"] = ay.group(1)

    # Period
    pf = re.search(r"From\s*:? (\d{2}-[A-Za-z]{3}-\d{4})", text)
    pt = re.search(r"To\s*:? (\d{2}-[A-Za-z]{3}-\d{4})", text)
    fields["period_from"] = pf.group(1) if pf else None
    fields["period_to"] = pt.group(1) if pt else None

    # Helper for amounts
    def find_amount(keyword, key):
        for l in lines:
            if keyword.lower() in l.lower():
                m = AMOUNT_REGEX.findall(l)
                if m: fields[key] = m[-1].replace(",", "")

    # Income & Tax
    find_amount("Gross Salary", "gross_salary")
    find_amount("exemption under section 10", "total_exemptions")
    find_amount("Standard deduction", "standard_deduction")
    find_amount("Tax on employment", "professional_tax")
    find_amount("Chapter VI-A", "total_deductions_chapter_VIA")
    find_amount("Total taxable income", "total_taxable_income")
    find_amount("Tax on total income", "tax_on_income")
    find_amount("Rebate under section 87A", "rebate_87A")
    find_amount("Health and education cess", "health_education_cess")
    find_amount("Relief under section 89", "relief_89")
    find_amount("Net tax payable", "net_tax_payable")
    find_amount("Tax Deducted", "tax_deducted")
    find_amount("Tax Deposited", "tax_deposited")

    return fields

def extract_form16(path: Path) -> dict:
    text = extract_text(path)
    if not text or len(text) < 200:
        text = ocr_text(path)
    return parse_fields(text)

def safe_float(value):
    try:
        if value is None:
            return 0
        return float(str(value).replace(",", ""))
    except ValueError:
        return 0

@csrf_exempt
def process_pdf(request):
    if request.method != "POST" or "file" not in request.FILES:
        return JsonResponse({"error": "POST request with PDF file required"}, status=400)

    uploaded_file = request.FILES["file"]

    if not uploaded_file.name.endswith(".pdf"):
        return JsonResponse({"error": "Only PDF files allowed"}, status=400)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = Path(tmp.name)

        # 1️⃣ Extract Form 16
        fields = extract_form16(tmp_path)
        print("\n===== Extracted Form 16 Fields =====")
        for k, v in fields.items():
            print(f"{k}: {v}")
        print("===================================\n")

        # 2️⃣ Prepare data for tax calculator
        gross_income = safe_float(fields.get("gross_salary"))
        # After extracting fields from PDF
        tds = fields.get("tax_deducted", 0) 

        gross_income = safe_float(fields.get("gross_salary"))

        deductions_dict = {
            "total_exemptions": safe_float(fields.get("total_exemptions")),
            "standard_deduction": safe_float(fields.get("standard_deduction")),
            "professional_tax": safe_float(fields.get("professional_tax")),
            "total_deductions_chapter_VIA": safe_float(fields.get("total_deductions_chapter_VIA")),
        }

        tds = fields.get("tax_deducted", 0) 
        age = 30  # default, or get from request.POST if available
        tds = fields.get("tax_deducted", 0)
        taxpayer_type = "resident"  # default, could enhance later

        # Outlier removal
        all_numeric = [gross_income] + [v for v in deductions_dict.values()]
        mean = np.mean(all_numeric)
        std = np.std(all_numeric)

        def remove_outlier(x):
            return x if std == 0 or abs(x - mean)/std < 3 else mean

        gross_income = remove_outlier(gross_income)
        deductions_dict = {k: remove_outlier(v) for k, v in deductions_dict.items()}




        # Deduction and taxable income
        total_deductions = calculate_deductions(deductions_dict, age)
        taxable_income = max(0, gross_income - total_deductions)

        # Calculate taxes
        # Ensure numeric safety
        tax_old = safe_float(resident_tax_old(taxable_income, age))
        tax_new = safe_float(resident_tax_new(gross_income))

        tax_old = safe_float(apply_surcharge(tax_old, taxable_income))
        tax_old = safe_float(apply_cess(tax_old))

        tax_new = safe_float(apply_surcharge(tax_new, gross_income))
        tax_new = safe_float(apply_cess(tax_new))

        tds = safe_float(tds)  # ensure tds is a number

        # Refund / payable safely
        result_data = {}

        if tds > tax_old:
            result_data["refund_old"] = tds - tax_old
        elif tax_old > tds:
            result_data["payable_old"] = tax_old - tds
        else:
            result_data["message_old"] = "No refund or payable"

        if tds > tax_new:
            result_data["refund_new"] = tds - tax_new
        elif tax_new > tds:
            result_data["payable_new"] = tax_new - tds
        else:
            result_data["message_new"] = "No refund or payable"

        # Final response
        response = {
            "gross_income": gross_income,
            "deductions": total_deductions,
            "taxable_income": taxable_income,
            "total_tax_old": tax_old,
            "total_tax_new": tax_new,
            "tax_details": result_data
        }

        print("\n===== Calculated Tax Details =====")
        print(json.dumps(response, indent=4))
        print("=================================\n")

        return JsonResponse(response)

    except Exception as e:
        print("Error in process_pdf_and_calculate_tax:", e)
        return JsonResponse({"error": str(e)}, status=500)










def get_comparison_graph_data(user_input: dict):
    """
    Compare user input tax calculation with historical data for plotting.
    """
    gross_income = user_input.get("gross_income")
    taxpayer_type = user_input.get("taxpayer_type")
    regime = user_input.get("regime")

    # Fetch historical data
    queryset = TaxCalculation.objects.all()
    if taxpayer_type:
        queryset = queryset.filter(taxpayer_type=taxpayer_type)
    if regime:
        queryset = queryset.filter(regime=regime)

    queryset = queryset.order_by("gross_income")

    historical_data = [
        {
            "gross_income": item.gross_income,
            "taxable_income": item.taxable_income,
            "total_tax": item.total_tax,
            "created_at": item.created_at.isoformat(),
        }
        for item in queryset
    ]

    # User input data for comparison
    user_data = {
        "gross_income": gross_income,
        "taxable_income": user_input.get("taxable_income"),
        "total_tax": user_input.get("total_tax"),
        "total_tax_new": user_input.get("total_tax_new"),
        "total_tax_old": user_input.get("total_tax_old"),
        "created_at": "current_input",
    }

    return {
        "historical": historical_data,
        "user_input": [user_data],
    }

@csrf_exempt
def upload_pdf(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]

        # Only accept PDFs
        if not uploaded_file.name.endswith(".pdf"):
            return JsonResponse({"error": "Only PDF files are allowed!"}, status=400)

        # fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, "pdfs"))
        # filename = fs.save(uploaded_file.name, uploaded_file)
        # file_url = fs.url(filename)

        return JsonResponse({"message": "PDF uploaded successfully!",})

    return JsonResponse({"error": "No file received"}, status=400)



@csrf_exempt
def tax_calculator_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)

    try:
        data = json.loads(request.body)

        # -------------------------------
        # User handling
        # -------------------------------
        username = data.get("username")
        user_email = data.get("email")

        user = None
        if username:
            user = UserAccount.objects.filter(username=username).first()
        elif user_email:
            user = UserAccount.objects.filter(email=user_email).first()

        # -------------------------------
        # Extract tax details
        # -------------------------------
        taxpayer_type = data.get("taxpayer_type", "resident")
        gross_income = float(data.get("gross_income", 0))
        age = int(data.get("age", 30))
        tds = float(data.get("tds", 0))
        deductions = data.get("deductions", {})
        has_business = data.get("has_business", False)
        presumptive = data.get("presumptive", False)
        special_income = data.get("special_income", False)

        # -------------------------------
        # Outlier Removal
        # -------------------------------
        all_numeric = [gross_income] + [float(v) for v in deductions.values()]
        mean = np.mean(all_numeric)
        std = np.std(all_numeric)

        def remove_outlier(x):
            return x if std == 0 or abs(x - mean) / std < 3 else mean

        gross_income = remove_outlier(gross_income)
        deductions = {k: remove_outlier(float(v)) for k, v in deductions.items()}

        # -------------------------------
        # Deductions & Taxable Income
        # -------------------------------
        total_deductions = calculate_deductions(deductions, age)
        taxable_income = max(0, gross_income - total_deductions)

        # -------------------------------
        # Calculate both old and new regime taxes
        # -------------------------------
        if taxpayer_type == "resident":
            tax_old = resident_tax_old(taxable_income, age)
            tax_new = resident_tax_new(gross_income)  # New regime ignores deductions
        elif taxpayer_type == "senior":
            tax_old = resident_tax_old(taxable_income, age)
            tax_new = resident_tax_new(gross_income)
        elif taxpayer_type == "nri":
            tax_old = nri_tax(taxable_income)
            tax_new = nri_tax(gross_income)
        elif taxpayer_type == "huf":
            tax_old = huf_tax(taxable_income)
            tax_new = huf_tax(gross_income)
        else:
            tax_old = resident_tax_old(taxable_income, age)
            tax_new = resident_tax_new(gross_income)

        tax_old = apply_surcharge(tax_old, taxable_income)
        tax_old = apply_cess(tax_old)

        tax_new = apply_surcharge(tax_new, gross_income)
        tax_new = apply_cess(tax_new)

        # -------------------------------
        # Refund or payable
        # -------------------------------
        result_data = {}
        if tds > tax_old:
            result_data["refund_old"] = tds - tax_old
        elif tax_old > tds:
            result_data["payable_old"] = tax_old - tds
        else:
            result_data["message_old"] = "No refund or payable"

        if tds > tax_new:
            result_data["refund_new"] = tds - tax_new
        elif tax_new > tds:
            result_data["payable_new"] = tax_new - tds
        else:
            result_data["message_new"] = "No refund or payable"

        # -------------------------------
        # Prepare comparison data
        # -------------------------------
        user_input = {
            "gross_income": gross_income,
            "taxable_income": taxable_income,
            "total_tax_old": tax_old,
            "total_tax_new": tax_new,
            "taxpayer_type": taxpayer_type,
        }
        comparison_data = get_comparison_graph_data(user_input)

        # -------------------------------
        # Final response
        # -------------------------------
        result_data.update(
            {
                "gross_income": gross_income,
                "deductions": total_deductions,
                "taxable_income": taxable_income,
                "total_tax_old": tax_old,
                "total_tax_new": tax_new,
                "itr_form": suggest_itr_form(
                    taxpayer_type, has_business, presumptive, special_income
                ),
                "comparison_graph": comparison_data,
            }
        )

        # -------------------------------
        # Save calculation to DB
        # -------------------------------
        tax_record = TaxCalculation(
            user=user,  # now linked to UserAccount if found
            taxpayer_type=taxpayer_type,
            regime="both",
            gross_income=gross_income,
            age=age,
            tds=tds,
            deductions=deductions,
            has_business=has_business,
            presumptive=presumptive,
            special_income=special_income,
            taxable_income=taxable_income,
            total_tax=max(tax_old, tax_new),
            result=result_data,
        )

        try:
            tax_record.save()
        except Exception as e:
            print("Error saving tax record:", e)

        return JsonResponse(result_data)

    except Exception as e:
        print("Error in tax_calculator_view:", e)
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def tax_history_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=400)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        user_email = data.get("email")

        if not username and not user_email:
            return JsonResponse({"error": "Username or Email is required"}, status=400)

        # Fetch user instance
        user = None
        if username:
            user = UserAccount.objects.filter(username=username).first()
        elif user_email:
            user = UserAccount.objects.filter(email=user_email).first()

        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        # Fetch tax calculation history for this user
        history = TaxCalculation.objects.filter(user=user).order_by("-created_at")

        # Serialize data
        history_data = [
            {
                "id": item.id,
                "gross_income": item.gross_income,
                "taxable_income": item.taxable_income,
                "total_tax": item.total_tax,
                "created_at": item.created_at.isoformat(),
            }
            for item in history
        ]

        return JsonResponse(history_data, safe=False)

    except Exception as e:
        print("Error in tax_history_api:", e)
        return JsonResponse({"error": str(e)}, status=500)
