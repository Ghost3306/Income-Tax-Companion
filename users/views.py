# views.py
from django.http import JsonResponse,HttpResponse,HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from .models import UserAccount
import json, uuid
from django.db.models import Q
from django.shortcuts import render, redirect


@csrf_exempt
def register(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")

            if not username or not email or not password:
                return JsonResponse({"error": "All fields required"}, status=400)

            # if UserAccount.objects.filter(username=username).exists():
            #     return JsonResponse({"error": "Username already exists"}, status=400)
            if UserAccount.objects.filter(email=email).exists():
                return JsonResponse({"error": "Email already registered"}, status=400)

            user = UserAccount(username=username, email=email)
            user.set_password(password)
            user.verification_token = uuid.uuid4()
            user.save()

            verify_link = request.build_absolute_uri(f"/accounts/verify/{user.verification_token}/")

            send_mail(
                "Verify your account",
                f"Click the link to verify your account: {verify_link}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            return JsonResponse({"message": "User registered, check email to verify"})
        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=405)   


def verify_account(request, token):
    message = ""
    alert_type = "info"  # bootstrap alert class

    try:
        user = UserAccount.objects.get(verification_token=token)
        if user.is_verified:
            message = "Account already verified"
            alert_type = "warning"
        else:
            user.is_verified = True
            user.save()
            message = "Account verified successfully"
            alert_type = "success"
    except UserAccount.DoesNotExist:
        message = "Invalid verification token"
        alert_type = "danger"

    return render(request, "index.html", {"message": message, "alert_type": alert_type})


@csrf_exempt
def login_view(request):
    if request.method == "OPTIONS":  # handle preflight for CORS
        response = HttpResponse()
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    if request.method == "POST":
        try:
            raw_body = request.body.decode("utf-8")
            print("RAW BODY:", raw_body)

            data = json.loads(raw_body)
            username_or_email = data.get("username")
            password = data.get("password")

            print("Login attempt:", username_or_email, "->", password)

            # ✅ Allow login with username OR email
            user = UserAccount.objects.get(
                Q(username=username_or_email) | Q(email=username_or_email)
            )

            if not user.is_verified:
                return JsonResponse({"error": "Account not verified"}, status=403)

            if user.check_password(password):
                return JsonResponse({
                    "message": "Login successful",
                    "username": user.username,
                    "full_name": user.username  
                })
            else:
                return JsonResponse({"error": "Invalid password"}, status=400)

        except UserAccount.DoesNotExist:
            return JsonResponse({"error": "Invalid username or email"}, status=400)
        except Exception as e:
            print(e)
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=405)

@csrf_exempt
def forgot_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")

        try:
            user = UserAccount.objects.get(email=email)
            user.reset_token = uuid.uuid4()
            user.save()

            reset_link = request.build_absolute_uri(f"/accounts/reset-password/{user.reset_token}/")
            send_mail(
                "Reset your password",
                f"Click the link to reset your password: {reset_link}",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            return JsonResponse({"message": "Password reset link sent"})
        except UserAccount.DoesNotExist:
            return JsonResponse({"error": "Email not found"}, status=404)

    return JsonResponse({"error": "Invalid request"}, status=405)

@csrf_exempt
def reset_password(request, token):
    message = None
    alert_type = None

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        try:
            user = UserAccount.objects.get(reset_token=token)
            user.set_password(new_password)
            user.reset_token = None
            user.save()

            # Redirect to frontend login page after success
            return HttpResponseRedirect("http://localhost:8080/")
        except UserAccount.DoesNotExist:
            message = "Invalid reset token"
            alert_type = "danger"

    return render(request, "reset_password.html", {"message": message, "alert_type": alert_type})