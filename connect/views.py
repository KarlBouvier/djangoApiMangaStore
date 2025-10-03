from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from produit.models import Manga, Tome, Category
from produit.serializer import MangaSerializer
from django.db import models
from django.db.models import Prefetch
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def collection_view(request):
    """
    API endpoint to get user's manga collection with pagination
    Query params: page (page number), page_size (items per page, default 10)
    Returns: JSON with user's collection of tomes grouped by manga and pagination info
    """
    # Get pagination parameters
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)
    
    try:
        page = int(page)
        page_size = int(page_size)
        # Limit page_size to prevent abuse
        page_size = min(page_size, 100)
    except ValueError:
        page = 1
        page_size = 10
    
    user = request.user
    collection_tomes = user.tomes_possedes.select_related('manga').order_by('manga__nom', 'numero')

    # Group tomes by manga
    mangas_dict = {}
    for tome in collection_tomes:
        manga = tome.manga
        if manga.nom not in mangas_dict:
            mangas_dict[manga.nom] = {
                'id': manga.id,
                'nom': manga.nom,
                # 'auteur': manga.auteur,
                'prix': float(manga.prix),
                'tomes': []
            }
        mangas_dict[manga.nom]['tomes'].append({
            "id": tome.id,
            "numero": tome.numero,
        })

    # Convert to list and apply pagination
    mangas_list = list(mangas_dict.values())
    paginator = Paginator(mangas_list, page_size)
    
    try:
        paginated_mangas = paginator.page(page)
    except PageNotAnInteger:
        paginated_mangas = paginator.page(1)
    except EmptyPage:
        paginated_mangas = paginator.page(paginator.num_pages)

    return Response({
        "mangas_collection": list(paginated_mangas),
        "total_tomes": collection_tomes.count(),
        "pagination": {
            'current_page': paginated_mangas.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'page_size': page_size,
            'has_next': paginated_mangas.has_next(),
            'has_previous': paginated_mangas.has_previous(),
            'next_page': paginated_mangas.next_page_number() if paginated_mangas.has_next() else None,
            'previous_page': paginated_mangas.previous_page_number() if paginated_mangas.has_previous() else None,
        }
    })
  
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recherche_view(request):
    """
    API endpoint to search for mangas with filters and pagination
    Query params: q (manga name), category (category id/slug), tome (tome number), 
                 page (page number), page_size (items per page, default 10)
    Returns: JSON with filtered mangas, available categories, and pagination info
    """
    # Get pagination parameters
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)
    
    try:
        page = int(page)
        page_size = int(page_size)
        # Limit page_size to prevent abuse
        page_size = min(page_size, 100)
    except ValueError:
        page = 1
        page_size = 10
    
    # Build a single filtered queryset; avoid broad all() evaluation and N+1s
    filters = models.Q()

    q = request.GET.get('q')
    
    category_list = request.GET.getlist('category')
    if not category_list:
        single_category = request.GET.get('category')
        if single_category:
            category_list = [c.strip() for c in single_category.split(',') if c.strip()]
    tome_num = request.GET.get('tome')

    if q:
        filters &= models.Q(nom__icontains=q.strip())

    needs_distinct = False
    if category_list:
        ids = []
        slugs = []
        for t in category_list:
            try:
                ids.append(int(t))
            except ValueError:
                slugs.append(t)
        q_filter = models.Q()
        if ids:
            q_filter |= models.Q(categories__id__in=ids)
        if slugs:
            q_filter |= models.Q(categories__slug__in=slugs)
        filters &= q_filter
        needs_distinct = True

    if tome_num:
        try:
            num = int(tome_num)
            filters &= models.Q(tomes__numero=num)
            needs_distinct = True
        except ValueError:
            pass

    prefetch_categories = Prefetch(
        'categories',
        queryset=Category.objects.only('id', 'name', 'slug'),
        to_attr='prefetched_categories'
    )

    mangas = (
        Manga.objects.filter(filters)
        .prefetch_related(prefetch_categories)
        .order_by('nom')
    )
    if needs_distinct:
        mangas = mangas.distinct()

    # Apply pagination
    paginator = Paginator(mangas, page_size)
    
    try:
        paginated_mangas = paginator.page(page)
    except PageNotAnInteger:
        paginated_mangas = paginator.page(1)
    except EmptyPage:
        paginated_mangas = paginator.page(paginator.num_pages)

    # Serialize manga results
    manga_list = []
    for manga in paginated_mangas:
        manga_list.append({
            'id': manga.id,
            'nom': manga.nom,
            'prix': float(manga.prix),
            'categories': [
                {'id': cat.id, 'name': cat.name, 'slug': cat.slug}
                for cat in getattr(manga, 'prefetched_categories', [])
            ]
        })

    # Serialize categories
    categories = Category.objects.only('id', 'name', 'slug').order_by('name')
    category_list_result = [
        {'id': cat.id, 'name': cat.name, 'slug': cat.slug}
        for cat in categories
    ]

    return Response({
        "mangas": manga_list,
        "categories": category_list_result,
        "pagination": {
            'current_page': paginated_mangas.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'page_size': page_size,
            'has_next': paginated_mangas.has_next(),
            'has_previous': paginated_mangas.has_previous(),
            'next_page': paginated_mangas.next_page_number() if paginated_mangas.has_next() else None,
            'previous_page': paginated_mangas.previous_page_number() if paginated_mangas.has_previous() else None,
        },
        "filters": {
            "q": q or "",
            "selected_categories": category_list,
            "selected_tome": tome_num or "",
        }
    })
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_mangas(request):
    """
    API endpoint to get all mangas with pagination
    Query params: page (page number), page_size (items per page, default 10)
    Returns: JSON with paginated mangas and pagination info
    """
    # Get pagination parameters
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)
    
    try:
        page = int(page)
        page_size = int(page_size)
        # Limit page_size to prevent abuse
        page_size = min(page_size, 100)
    except ValueError:
        page = 1
        page_size = 10
    
    # Get all mangas with prefetched categories
    mangas = Manga.objects.prefetch_related('categories').all().order_by('nom')
    
    # Create paginator
    paginator = Paginator(mangas, page_size)
    
    try:
        paginated_mangas = paginator.page(page)
    except PageNotAnInteger:
        paginated_mangas = paginator.page(1)
    except EmptyPage:
        paginated_mangas = paginator.page(paginator.num_pages)
    
    # Serialize the paginated results
    serializer = MangaSerializer(paginated_mangas, many=True)
    
    return Response({
        'mangas': serializer.data,
        'pagination': {
            'current_page': paginated_mangas.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'page_size': page_size,
            'has_next': paginated_mangas.has_next(),
            'has_previous': paginated_mangas.has_previous(),
            'next_page': paginated_mangas.next_page_number() if paginated_mangas.has_next() else None,
            'previous_page': paginated_mangas.previous_page_number() if paginated_mangas.has_previous() else None,
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def manga_detail_view(request, manga_id):
    """
    API endpoint to get details of a specific manga
    Returns: JSON with manga details and all its tomes
    """
    manga = get_object_or_404(Manga, id=manga_id)
    tomes = manga.tomes.all().order_by('numero')
    
    return Response({
        "manga": {
            "id": manga.id,
            "nom": manga.nom,
            "prix": float(manga.prix),
            "description": getattr(manga, 'description', ''),
        },
        "tomes": [
            {
                "id": tome.id,
                "numero": tome.numero,
                "cover": tome.get_signed_cover_url() if hasattr(tome, 'get_signed_cover_url') else (tome.cover.url if tome.cover else None),
            }
            for tome in tomes
        ]
    })
