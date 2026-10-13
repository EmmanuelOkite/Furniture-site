from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from .models import Product

# Longer queries are cut to this length; no one types a 100-character furniture search.
MAX_QUERY_LENGTH = 100
RESULTS_PER_PAGE = 12
COLLECTION_PER_PAGE = 24
FEATURED_LIMIT = 4


def home(request):
    featured = Product.objects.filter(is_active=True, is_featured=True)[:FEATURED_LIMIT]
    return render(request, 'home.html', {'featured_products': featured})


def collection(request):
    """All active products, optionally filtered by room (?room=bedroom)."""
    products = Product.objects.filter(is_active=True).order_by('room', 'name')

    # Ignore unknown room values instead of showing an empty page.
    room = request.GET.get('room', '')
    if room not in Product.Room.values:
        room = ''
    if room:
        products = products.filter(room=room)

    paginator = Paginator(products, COLLECTION_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'collection.html', {
        'page_obj': page_obj,
        'rooms': Product.Room.choices,
        'current_room': room,
        'current_room_label': Product.Room(room).label if room else '',
    })


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
