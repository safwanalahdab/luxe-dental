from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("products/<str:slug>/", views.product_detail, name="product_detail"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
]
