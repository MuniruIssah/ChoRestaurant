"""
Server-rendered / hybrid form views for Accounts (registration, login, logout, profile, addresses).
Supports standard HTML form submissions (for Developer 2's templates) and falls back cleanly
when templates are not yet rendered by Developer 2.
Owned by Developer 1.
"""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import select_template
from django.template import TemplateDoesNotExist
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


def _render_or_json(request: HttpRequest, template_names: list[str], context: dict, json_payload: dict, status: int = 200) -> HttpResponse:
    """
    Render the customer template if Developer 2 has created it or if a base template exists;
    otherwise return a clean JSON response when requested via Accept: application/json.
    """
    if "application/json" in request.headers.get("Accept", ""):
        return JsonResponse(json_payload, status=status)
    try:
        template = select_template(template_names)
        return HttpResponse(template.render(context, request), status=status)
    except TemplateDoesNotExist:
        return JsonResponse(json_payload, status=status)


@require_http_methods(["GET", "POST"])
def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = CustomerRegistrationForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("accounts:profile")
        return _render_or_json(
            request,
            ["customer/register.html", "accounts/register.html"],
            {"form": form},
            {"errors": form.errors},
            status=400,
        )

    return _render_or_json(
        request,
        ["customer/register.html", "accounts/register.html"],
        {"form": form},
        {"view": "register", "fields": list(form.fields.keys())},
    )


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("accounts:profile")

    form = EmailOrUsernameLoginForm(request, data=request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                return redirect(next_url)
            return redirect("accounts:profile")
        return _render_or_json(
            request,
            ["customer/login.html", "accounts/login.html"],
            {"form": form},
            {"errors": form.errors},
            status=401,
        )

    return _render_or_json(
        request,
        ["customer/login.html", "accounts/login.html"],
        {"form": form},
        {"view": "login", "fields": ["identifier", "password"]},
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

    if request.method == "POST":
        forms_valid = user_form.is_valid() and (pref_form.is_valid() if pref_form else True)
        if forms_valid:
            user_form.save()
            if pref_form:
                pref_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
        errors = {**user_form.errors}
        if pref_form:
            errors.update(pref_form.errors)
        return _render_or_json(
            request,
            ["customer/profile.html", "accounts/profile.html"],
            {"user_form": user_form, "pref_form": pref_form, "addresses": user.addresses.all()},
            {"errors": errors},
            status=400,
        )

    return _render_or_json(
        request,
        ["customer/profile.html", "accounts/profile.html"],
        {
            "user_form": user_form,
            "pref_form": pref_form,
            "addresses": user.addresses.all(),
        },
        {"user": UserSerializer(user).data},
    )


@login_required
@require_http_methods(["GET", "POST"])
def address_list_create_view(request: HttpRequest) -> HttpResponse:
    form = AddressForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Delivery address saved.")
            return redirect("accounts:addresses")
        return _render_or_json(
            request,
            ["customer/addresses.html", "accounts/addresses.html"],
            {"form": form, "addresses": request.user.addresses.all()},
            {"errors": form.errors},
            status=400,
        )

    addresses = request.user.addresses.all()
    return _render_or_json(
        request,
        ["customer/addresses.html", "accounts/addresses.html"],
        {"form": form, "addresses": addresses},
        {"addresses": AddressSerializer(addresses, many=True).data},
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
