from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def home(request):
    return render(
        request,
        "catalog/home.html",
        {
            "categories": Category.objects.all(),
            "featured_products": Product.objects.select_related("category")
            .filter(category__status=Category.Statuts.ACTIVE)
            .order_by("-created_at")[:4],
        },
    )


def product_list(request):
    products = Product.objects.select_related("category").filter(
        category__status=Category.Statuts.ACTIVE
    )
    selected_type = request.GET.get("type", "all")
    valid_types = {choice.value for choice in Product.ProductType}
    if selected_type in valid_types:
        products = products.filter(product_type=selected_type)
    else:
        selected_type = "all"

    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(brand__icontains=query)
            | Q(description__icontains=query)
        )

    return render(
        request,
        "catalog/product_list.html",
        {"products": products, "selected_type": selected_type, "query": query},
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category"), slug=slug
    )
    related_products = (
        Product.objects.select_related("category")
        .filter(category__status=Category.Statuts.ACTIVE)
        .exclude(pk=product.pk)[:4]
    )
    return render(
        request,
        "catalog/product_detail.html",
        {"product": product, "related_products": related_products},
    )


def about(request):
    return render(request, "about.html")


def contact(request):
    return render(request, "contact.html")
