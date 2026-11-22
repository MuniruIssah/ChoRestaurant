"""
Server-rendered / hybrid form views for Accounts (registration, login, logout, profile, addresses).
Supports Developer 2's customer templates when present, returns JSON when Accept: application/json
is requested, and renders a built-in Developer 1 verification HTML page in the browser otherwise.
Owned by Developer 1.
"""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.template import TemplateDoesNotExist
from django.template.loader import select_template
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.http import require_http_methods

from .forms import (
    AddressForm,
    CustomerNotificationPreferencesForm,
    CustomerRegistrationForm,
    EmailOrUsernameLoginForm,
    UserProfileUpdateForm,
)
from .models import Address, CustomerProfile
from .serializers import AddressSerializer, UserSerializer
from .services import set_default_address


def _wrap_html(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(title)} — Cho Restaurant</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; }}
        .box {{ max-width: 680px; margin: 0 auto; background: #1e293b; border: 1px solid #334155; border-radius: 0.75rem; padding: 1.75rem; }}
        h2 {{ margin-top: 0; color: #f59e0b; }}
        label {{ display: block; margin-top: 0.75rem; font-weight: 600; font-size: 0.9rem; }}
        input, select {{ width: 100%; padding: 0.55rem; margin-top: 0.25rem; border-radius: 0.4rem; border: 1px solid #475569; background: #0f172a; color: #f8fafc; box-sizing: border-box; }}
        input[type="checkbox"] {{ width: auto; margin-right: 0.5rem; }}
        button, .btn {{ display: inline-block; margin-top: 1rem; background: #f59e0b; color: #0f172a; border: none; padding: 0.6rem 1.1rem; border-radius: 0.45rem; font-weight: 700; cursor: pointer; text-decoration: none; }}
        .nav {{ margin-bottom: 1rem; font-size: 0.9rem; }}
        .nav a {{ color: #38bdf8; text-decoration: none; margin-right: 1rem; }}
        .card-item {{ border-top: 1px solid #334155; padding: 0.75rem 0; margin-top: 0.75rem; }}
        .errorlist {{ color: #f87171; padding-left: 1.2rem; }}
    </style>
</head>
<body>
    <div class="box">
        <div class="nav">
            <a href="/">← Foundation Home</a>
            <a href="/menu/">Menu</a>
            <a href="/accounts/profile/">Profile</a>
            <a href="/accounts/addresses/">Addresses</a>
            <a href="/admin/">Django Admin</a>
        </div>
        {body_html}
    </div>
</body>
</html>"""


def _render_or_fallback(
    request: HttpRequest,
    template_names: list[str],
    context: dict,
    json_payload: dict,
    fallback_title: str,
    fallback_body: str,
    status: int = 200,
) -> HttpResponse:
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse(json_payload, status=status)
    try:
        template = select_template(template_names)
        return HttpResponse(template.render(context, request), status=status)
    except TemplateDoesNotExist:
        return HttpResponse(_wrap_html(fallback_title, fallback_body), status=status)


@require_http_methods(["GET", "POST"])
def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = CustomerRegistrationForm(request.POST or None)
    status_code = 200
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("accounts:profile")
        status_code = 400

    csrf_token = get_token(request)
    body = f"""
        <h2>Customer Registration</h2>
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
            {form.as_p()}
            <button type="submit">Create Customer Account</button>
        </form>
        <p>Already have an account? <a href="{reverse('accounts:login')}" style="color:#38bdf8;">Sign in</a></p>
    """
    return _render_or_fallback(
        request,
        ["customer/register.html", "accounts/register.html"],
        {"form": form},
        {"view": "register", "errors": form.errors} if status_code == 400 else {"view": "register", "fields": list(form.fields.keys())},
        "Customer Registration",
        body,
        status=status_code,
    )


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = EmailOrUsernameLoginForm(request, data=request.POST or None)
    status_code = 200
    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("accounts:profile")
        status_code = 401

    csrf_token = get_token(request)
    body = f"""
        <h2>Sign In</h2>
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
            {form.as_p()}
            <button type="submit">Sign In</button>
        </form>
        <p style="font-size:0.85rem; color:#94a3b8;">
            Demo credentials: <code>customer_akua</code> / <code>CustomerPass123!</code> or <code>admin_cho</code> / <code>AdminPass123!</code>
        </p>
    """
    return _render_or_fallback(
        request,
        ["customer/login.html", "accounts/login.html"],
        {"form": form},
        {"view": "login", "errors": form.errors} if status_code != 200 else {"view": "login", "fields": ["identifier", "password"]},
        "Sign In",
        body,
        status=status_code,
    )


@require_http_methods(["POST", "GET"])
def logout_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request: HttpRequest) -> HttpResponse:
    user = request.user
    customer_profile = None
    if user.is_customer:
        customer_profile, _ = CustomerProfile.objects.get_or_create(user=user)

    user_form = UserProfileUpdateForm(request.POST or None, instance=user)
    pref_form = (
        CustomerNotificationPreferencesForm(request.POST or None, instance=customer_profile)
        if customer_profile
        else None
    )

    status_code = 200
    if request.method == "POST":
        forms_valid = user_form.is_valid() and (pref_form.is_valid() if pref_form else True)
        if forms_valid:
            user_form.save()
            if pref_form:
                pref_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
        status_code = 400

    csrf_token = get_token(request)
    pref_html = pref_form.as_p() if pref_form else ""
    body = f"""
        <h2>My Profile — {escape(user.username)} ({escape(user.role)})</h2>
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
            {user_form.as_p()}
            {pref_html}
            <button type="submit">Save Profile</button>
        </form>
        <p><a class="btn" href="{reverse('accounts:addresses')}" style="background:#38bdf8;">Manage Delivery Addresses</a>
           <a class="btn" href="{reverse('accounts:logout')}" style="background:#ef4444; color:white; margin-left:0.5rem;">Logout</a></p>
    """
    return _render_or_fallback(
        request,
        ["customer/profile.html", "accounts/profile.html"],
        {
            "user_form": user_form,
            "pref_form": pref_form,
            "addresses": user.addresses.all(),
        },
        {"user": UserSerializer(user).data},
        "My Profile",
        body,
        status=status_code,
    )


@login_required
@require_http_methods(["GET", "POST"])
def address_list_create_view(request: HttpRequest) -> HttpResponse:
    form = AddressForm(request.POST or None)
    status_code = 200
    if request.method == "POST":
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Delivery address saved.")
            return redirect("accounts:addresses")
        status_code = 400

    addresses = request.user.addresses.all()
    csrf_token = get_token(request)
    addr_items = []
    for addr in addresses:
        default_tag = " <strong>[Default]</strong>" if addr.is_default else ""
        addr_items.append(
            f"""
            <div class="card-item">
                <div><strong>{escape(addr.label)}</strong>{default_tag}: {escape(addr.line1)}, {escape(addr.city)}, {escape(addr.state)} ({escape(addr.country)})</div>
                <div style="font-size:0.85rem; color:#94a3b8;">GPS: {addr.latitude or 'N/A'}, {addr.longitude or 'N/A'}</div>
            </div>
            """
        )
    body = f"""
        <h2>Saved Delivery Addresses ({addresses.count()})</h2>
        {"".join(addr_items) or "<p>No saved delivery addresses yet.</p>"}
        <h3 style="margin-top:1.5rem;">Add New Address</h3>
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">
            {form.as_p()}
            <button type="submit">Save Delivery Address</button>
        </form>
    """
    return _render_or_fallback(
        request,
        ["customer/addresses.html", "accounts/addresses.html"],
        {"form": form, "addresses": addresses},
        {"addresses": AddressSerializer(addresses, many=True).data},
        "Saved Delivery Addresses",
        body,
        status=status_code,
    )


@login_required
@require_http_methods(["POST"])
def address_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    address = get_object_or_404(Address, pk=pk, user=request.user)
    was_default = address.is_default
    address.delete()
    if was_default:
        next_addr = Address.objects.filter(user=request.user).first()
        if next_addr:
            set_default_address(request.user, next_addr.pk)
    messages.success(request, "Delivery address removed.")
    return redirect("accounts:addresses")


@login_required
@require_http_methods(["POST"])
def address_set_default_view(request: HttpRequest, pk: int) -> HttpResponse:
    get_object_or_404(Address, pk=pk, user=request.user)
    set_default_address(request.user, pk)
    messages.success(request, "Default delivery address updated.")
    return redirect("accounts:addresses")
