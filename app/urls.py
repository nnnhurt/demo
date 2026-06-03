from django.urls import path

from app import views

urlpatterns = [
    path("", views.UserLoginView.as_view(), name="login"),
    path("products/", views.ProductListView.as_view(), name="product_list"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("products/add/", views.ProductCreateView.as_view(), name="product_add"),
    path(
        "products/<int:pk>/edit/",
        views.ProductUpdateView.as_view(),
        name="product_edit",
    ),
    path(
        "products/<int:pk>/delete/",
        views.ProductDeleteView.as_view(),
        name="product_delete",
    ),
    path("zakazy/", views.ZakazListView.as_view(), name="zakaz_list"),
    path("zakazy/add/", views.ZakazCreateView.as_view(), name="zakaz_add"),
    path("zakazy/<int:pk>/edit/", views.ZakazUpdateView.as_view(), name="zakaz_edit"),
    path(
        "zakazy/<int:pk>/delete/",
        views.ZakazDeleteView.as_view(),
        name="zakaz_delete",
    ),
]
