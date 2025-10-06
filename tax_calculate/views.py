
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import numpy as np
from tax_calculate.models import TaxCalculation
from users.models import UserAccount
from dotenv import load_dotenv
import os
import re

# Load variables from .env file
load_dotenv()

HF_API_KEY = os.getenv("HF_API_KEY")

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
import os
import tempfile
from pathlib import Path
import numpy as np
import pdfplumber
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from transformers import pipeline

import re

def safe_float(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    # Convert to string and clean
    s = str(val).replace(",", "").replace("\n", " ").strip()

    # Extract first valid number (handles cases like "873130.20 10")
    match = re.search(r"[-+]?\d*\.?\d+", s)
    if match:
        try:
            return float(match.group(0))
        except:
            return 0.0
    return 0.0

# Disable TensorFlow/Keras backend (to avoid Keras 3 issues)
os.environ["USE_TF"] = "0"

# -------------------------------
# AI-powered Form16 Extractor
# -------------------------------
import os
import re
import tempfile
from pathlib import Path
import numpy as np
import pdfplumber
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from transformers import pipeline

# Disable TensorFlow/Keras backend (to avoid Keras 3 conflicts)
os.environ["USE_TF"] = "0"


# -------------------------------
# Utility: Safe float conversion
# -------------------------------
def safe_float(val):
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).replace(",", "").replace("\n", " ").strip()
    # Extract first valid number
    match = re.search(r"[-+]?\d*\.?\d+", s)
    if match:
        try:
            return float(match.group(0))
        except:
            return 0.0
    return 0.0


# -------------------------------
# AI-powered Form16 Extractor
# -------------------------------
def parse_form16_ai(pdf_path):
    data = {
        "employer": {},
        "employee": {},
        "taxpayer_type": "resident",
        "assessment_year": None,
        "gross_income": 0.0,
        "salary_components": {},
        "exemptions": {},
        "deductions": {},
        "other_income": {},
        "tds": 0.0,
        "tax_summary": {}
    }

    # Step 1: Extract text
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text()
            if txt:
                text += txt + "\n"

    # Step 2: Hugging Face QA pipeline
    qa_model = pipeline("question-answering", model="distilbert-base-cased-distilled-squad")

    def ask(question):
        try:
            ans = qa_model(question=question, context=text)
            return ans['answer']
        except:
            return None

    # Step 3: Extract details
    data["employee"]["PAN"] = ask("What is the PAN of the employee?")
    data["employer"]["PAN"] = ask("What is the PAN of the deductor?")
    data["employer"]["TAN"] = ask("What is the TAN of the deductor?")
    data["assessment_year"] = ask("What is the assessment year?")
    data["gross_income"] = safe_float(ask("What is the gross salary?"))
    data["tds"] = safe_float(ask("What is the total tax deducted?"))

    # Deduction sections (80C, 80D, etc.)
    for sec in ["80C", "80CCC", "80CCD", "80D", "80E", "80G", "80TTA", "80TTB"]:
        val = safe_float(ask(f"What is the deduction under section {sec}?"))
        if val > 0:
            data["deductions"][sec] = val

    # Salary parts
    for part in ["Salary as per section 17(1)", "Value of perquisites under section 17(2)",
                 "Profits in lieu of salary under section 17(3)"]:
        val = safe_float(ask(f"What is the {part}?"))
        if val > 0:
            key = part.split()[0]
            data["salary_components"][key] = val

    # Tax Summary
    for field in ["Tax on total income", "Rebate under section 87A", "Surcharge",
                  "Health and education cess", "Tax payable", "Relief under section 89"]:
        val = safe_float(ask(f"What is the {field}?"))
        if val > 0:
            data["tax_summary"][field] = val

    # Senior citizen detection
    if "specified senior citizen" in text.lower():
        data["taxpayer_type"] = "senior citizen"

    # Step 4: Outlier removal
    all_numeric = [data["gross_income"], data["tds"]] + list(data["deductions"].values())
    if all_numeric:
        mean = np.mean(all_numeric)
        std = np.std(all_numeric)

        def remove_outlier(x):
            return x if std == 0 or abs(x - mean) / std < 3 else mean

        data["gross_income"] = remove_outlier(data["gross_income"])
        data["tds"] = remove_outlier(data["tds"])
        data["deductions"] = {k: remove_outlier(v) for k, v in data["deductions"].items()}

    return data


# -------------------------------
# Django View
# -------------------------------
@csrf_exempt
def process_pdf(request):
    if request.method != "POST" or "file" not in request.FILES:
        return JsonResponse({"error": "POST request with PDF file required"}, status=400)

    uploaded_file = request.FILES["file"]
    if not uploaded_file.name.endswith(".pdf"):
        return JsonResponse({"error": "Only PDF files allowed"}, status=400)

    try:
        # Save uploaded PDF temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = Path(tmp.name)

        # Use AI parser
        fields = parse_form16_ai(tmp_path)
        print("Extracted fields:", fields)

        # Prepare cleaned payload
        payload = {
            "extracted_fields": fields,
            "cleaned": {
                "gross_income": safe_float(fields.get("gross_income")),
                "tds": safe_float(fields.get("tds")),
                "taxpayer_type": fields.get("taxpayer_type", "resident"),
            },
        }

        tmp_path.unlink(missing_ok=True)
        return JsonResponse(payload)

    except Exception as e:
        print("Error in process_pdf:", e)
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

import json
import os
import numpy as np
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import TaxCalculation, UserAccount
from tax_calculate.calculators import (
    calculate_deductions,
    resident_tax_old,
    resident_tax_new,
    nri_tax,
    huf_tax,
    apply_surcharge,
    apply_cess,
    suggest_itr_form,
 
)

# -------------------------------
# Load tax-saving policies JSON
# -------------------------------
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# with open(os.path.join(BASE_DIR, "tax_saving_policies.json"), "r") as f:
#     TAX_SAVING_POLICIES = json.load(f)


# @csrf_exempt
# def tax_calculator_view(request):
#     if request.method != "POST":
#         return JsonResponse({"error": "POST method required"}, status=400)

#     try:
#         data = json.loads(request.body)

#         # -------------------------------
#         # User handling
#         # -------------------------------
#         username = data.get("username")
#         user_email = data.get("email")

#         user = None
#         if username:
#             user = UserAccount.objects.filter(username=username).first()
#         elif user_email:
#             user = UserAccount.objects.filter(email=user_email).first()

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
#             return x if std == 0 or abs(x - mean) / std < 3 else mean

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
#             tax_new = resident_tax_new(gross_income)
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
#             "taxpayer_type": taxpayer_type,
#         }
#         comparison_data = get_comparison_graph_data(user_input)

#         # -------------------------------
#         # Recommended Policies
#         # -------------------------------
#         recommended_policies = []
#         for category, data in TAX_SAVING_POLICIES.items():
#             current_value = float(deductions.get(category, 0))
#             limit = data["limit"]
#             if limit == "No limit":
#                 if current_value == 0:
#                     recommended_policies.append({category: data["policies"]})
#             elif current_value < limit:
#                 recommended_policies.append({category: data["policies"]})

#         # -------------------------------
#         # Final response
#         # -------------------------------
#         result_data.update(
#             {
#                 "gross_income": gross_income,
#                 "deductions": total_deductions,
#                 "taxable_income": taxable_income,
#                 "total_tax_old": tax_old,
#                 "total_tax_new": tax_new,
#                 "itr_form": suggest_itr_form(
#                     taxpayer_type, has_business, presumptive, special_income
#                 ),
#                 "comparison_graph": comparison_data,
#                 "recommended_policies": recommended_policies
#             }
#         )

#         # -------------------------------
#         # Save calculation to DB
#         # -------------------------------
#         tax_record = TaxCalculation(
#             user=user,
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
#             result=result_data,
#         )

#         try:
#             tax_record.save()
#         except Exception as e:
#             print("Error saving tax record:", e)

#         return JsonResponse(result_data)

#     except Exception as e:
#         print("Error in tax_calculator_view:", e)
#         return JsonResponse({"error": str(e)}, status=500)


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

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
import json
from .utils import predict_response
from .models import ChatSession, ChatLog

@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST allowed")
    try:
        payload = json.loads(request.body.decode("utf-8"))
        query = payload.get("query", "")
        session_id = payload.get("session_id")
        if not query:
            return JsonResponse({"error":"query field required"}, status=400)
        
        result = predict_response(query, session_id=session_id)

        if session_id:
            session, _ = ChatSession.objects.get_or_create(session_id=session_id)
            ChatLog.objects.create(
                session=session,
                user_message=query,
                bot_response=result["response"],
                intent=result["intent"],
                confidence=result["confidence"]
            )

        return JsonResponse({
            "query": query,
            "intent": result["intent"],
            "response": result["response"],
            "confidence": result["confidence"],
            "normalized": result["normalized"]
        })
    except json.JSONDecodeError:
        return JsonResponse({"error":"invalid json"}, status=400)
    except Exception as exc:
        print("Error:", exc)
        return JsonResponse({"error": str(exc)}, status=500)


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .utils import load_model, normalize_text, correct_spelling, censor  # existing chatbot utils
from .models import ChatSession, ChatLog
import random
import json
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import FAQ  # import your FAQ model

@csrf_exempt
def faq_api(request):
    """
    API for FAQ queries.
    Returns multiple FAQs from the FAQ model based on user's query.
    If query is empty or None, returns 6–10 random FAQs.
    Otherwise, returns FAQs whose question or answer contains the query.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        query = payload.get("query", "").strip()

        if not query:
            # Return random 6–10 FAQs
            all_faqs = list(FAQ.objects.all())
            if len(all_faqs) > 10:
                results = random.sample(all_faqs, k=random.randint(6, 10))
            else:
                results = all_faqs
        else:
            # Filter FAQs by query in question or answer
            results = list(
                FAQ.objects.filter(question__icontains=query) |
                FAQ.objects.filter(answer__icontains=query)
            )

        # Format results for frontend
        results_json = [
            {
                "question": faq.question,
                "answer": faq.answer,
                "category": getattr(faq, "category", "")
            } for faq in results
        ]

        return JsonResponse({"query": query, "results": results_json})

    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)



import json
import random
from django.http import JsonResponse
from .models import FAQ

def random_faqs(request):
    """
    Returns 6-10 random FAQ entries in JSON format.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Only GET allowed"}, status=400)

    faqs = list(FAQ.objects.all())
    if not faqs:
        return JsonResponse({"faqs": []})

    count = min(len(faqs), random.randint(6, 10))
    selected = random.sample(faqs, count)
    data = [{"id": f.id, "question": f.question, "answer": f.answer} for f in selected]
    print(data)
    return JsonResponse({"faqs": data})

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import FAQ

@csrf_exempt
def insert_faq_query(request):
    """
    API to insert a new FAQ query.
    Only 'question' is required. Answer, category, and email are optional.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
        question = data.get("question", "").strip()
        category = data.get("category", "").strip() if data.get("category") else None
        email = data.get("email", "").strip() if data.get("email") else None
        print(email)
        if not question:
            return JsonResponse({"error": "Question is required"}, status=400)

        faq = FAQ.objects.create(question=question, category=category, email=email)
        return JsonResponse({
            "message": "FAQ query saved successfully",
            "faq": {
                "id": str(faq.id),
                "question": faq.question,
                "answer": faq.answer,
                "category": faq.category,
                "email": faq.email
            }
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import FAQ
import json

@csrf_exempt
def fetch_faq_by_email(request):
    """
    API to fetch FAQ queries based on email.
    Returns all FAQs submitted by the provided email.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
        email = data.get("email", "").strip()

        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)

        faqs = FAQ.objects.filter(email=email).order_by('-created_at')
        faq_list = [
            {
                "id": str(faq.id),
                "question": faq.question,
                "answer": faq.answer,
                "category": faq.category,
                "email": faq.email,
            }
            for faq in faqs
        ]

        return JsonResponse({"faqs": faq_list, "count": len(faq_list)}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
