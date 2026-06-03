from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView
from extra_views import CreateWithInlinesView, UpdateWithInlinesView

from demo.context_processors import get_skidka_groups

from app.forms import ProductForm, ZakazForm, ZakazItemInline
from app.models import Product, Zakaz, ZakazItem


class UserLoginView(LoginView):
    template_name = "app/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("product_list")


class LogoutView(View):
    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        logout(request)
        return redirect("product_list")


class ProductListView(ListView):
    model = Product
    template_name = "app/product_list.html"
    context_object_name = "products"

    def get_queryset(self):
        queryset = Product.objects.select_related(
            "category", "manufacturer", "supplier", "unit"
        )
        if not self.request.user.is_authenticated or self.request.user.role not in (
            "manager",
            "admin",
        ):
            return queryset

        search_query = self.request.GET.get("search", "")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(manufacturer__name__icontains=search_query)
                | Q(category__name__icontains=search_query)
                | Q(supplier__name__icontains=search_query)
            )
        # диапазон скидок берется из настроек
        skidka_query = self.request.GET.get("skidka", "")
        bounds = get_skidka_groups().get(skidka_query)
        if bounds is not None:
            min_skidka, max_skidka = bounds
            queryset = queryset.filter(
                skidka__gte=min_skidka,
                skidka__lte=max_skidka,
            )

        order_fields: list[str] = []
        for param, field in (
            ("sort_quantity", "quantity"),
            ("sort_price", "price"),
            ("sort_skidka", "skidka"),
        ):
            direction = self.request.GET.get(param, "")
            if direction == "asc":
                order_fields.append(field)
            elif direction in ("desc", "down"):
                order_fields.append(f"-{field}")
        if order_fields:
            queryset = queryset.order_by(*order_fields)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_search"] = (self.request.GET.get("search") or "").strip()
        context["current_skidka"] = self.request.GET.get("skidka", "")
        context["current_sort_quantity"] = self.request.GET.get("sort_quantity", "")
        context["current_sort_price"] = self.request.GET.get("sort_price", "")
        context["current_sort_skidka"] = self.request.GET.get("sort_skidka", "")
        return context


class AdminMixin(UserPassesTestMixin):
    login_url = reverse_lazy("login")

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role == "admin"


class ManagerAdminMixin(UserPassesTestMixin):
    login_url = reverse_lazy("login")

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.role in ("admin", "manager")


class ProductCreateView(AdminMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "app/product_form.html"
    success_url = reverse_lazy("product_list")

    def form_valid(self, form):
        messages.success(self.request, "Товар успешно добавлен")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class ProductUpdateView(AdminMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "app/product_form.html"
    success_url = reverse_lazy("product_list")

    def form_valid(self, form):
        messages.success(self.request, "Товар успешно обновлен")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context


class ProductDeleteView(AdminMixin, View):
    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        product = Product.objects.filter(pk=pk).first()
        if not product:
            return redirect("product_list")
        if ZakazItem.objects.filter(product=product).exists():
            messages.error(request, "Нельзя удалить товар: он присутствует в заказе.")
            return redirect("product_list")
        product.delete()
        messages.success(request, "Товар удалён")
        return redirect("product_list")


class ZakazListView(LoginRequiredMixin, ManagerAdminMixin, ListView):
    model = Zakaz
    template_name = "app/zakaz_list.html"
    context_object_name = "zakazy"
    login_url = reverse_lazy("login")

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated and request.user.role not in ("admin", "manager"):
            return redirect("product_list")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Zakaz.objects.select_related("punkt", "client")
            .prefetch_related("items__product")
            .order_by("-zakaz_date", "-id")
        )


class ZakazCreateView(AdminMixin, CreateWithInlinesView):
    model = Zakaz
    form_class = ZakazForm
    template_name = "app/zakaz_form.html"
    inlines = [ZakazItemInline]
    success_url = reverse_lazy("zakaz_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = False
        return context


class ZakazUpdateView(AdminMixin, UpdateWithInlinesView):
    model = Zakaz
    form_class = ZakazForm
    template_name = "app/zakaz_form.html"
    inlines = [ZakazItemInline]
    success_url = reverse_lazy("zakaz_list")

    def form_valid(self, form):
        messages.success(self.request, "Заказ успешно обновлен")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_edit"] = True
        return context


class ZakazDeleteView(AdminMixin, View):
    def post(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        Zakaz.objects.filter(pk=pk).delete()
        messages.success(request, "Заказ удалён")
        return redirect("zakaz_list")
