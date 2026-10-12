from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import Product

# Longer queries are cut to this length; no one types a 100-character furniture search.
MAX_QUERY_LENGTH = 100
RESULTS_PER_PAGE = 12


def home(request):
    return render(request, 'home.html')


def search_products(query):
    """
    Return active products matching every word in ``query``.

    Each word may match the name, type, description or room, case-insensitively,
    so "green sofa" finds products that mention both "green" and "sofa".
    """
    products = Product.objects.filter(is_active=True)

    for word in query.split():
        # Rooms are stored as codes ("living-room"), so match the word against
        # their display labels ("Living Room") instead.
        matching_rooms = [
            value for value, label in Product.Room.choices if word.lower() in label.lower()
        ]
        products = products.filter(
            Q(name__icontains=word)
            | Q(product_type__icontains=word)
            | Q(description__icontains=word)
            | Q(room__in=matching_rooms)
        )

    return products


def search(request):
    query = request.GET.get('q', '').strip()[:MAX_QUERY_LENGTH]

    page_obj = None
    if query:
        paginator = Paginator(search_products(query), RESULTS_PER_PAGE)
        page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'search.html', {
        'query': query,
        'page_obj': page_obj,
    })
