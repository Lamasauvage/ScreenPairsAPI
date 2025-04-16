from django.conf import settings
from django_ratelimit.decorators import ratelimit
from rest_framework.decorators import api_view
from rest_framework.response import Response
from services.tmdb import find_common_movies, search_actors


@api_view(['GET'])
@ratelimit(key='ip', rate=settings.ACTOR_RATE, method='GET', block=True)
def actor_autocomplete(request):
    query = request.GET.get('query', '')
    results = search_actors(query)
    return Response({'results': results})


@api_view(['GET'])
@ratelimit(key='ip', rate=settings.MOVIES_RATE, method='GET', block=True)
def common_movies_view(request):
    actor1 = request.GET.get('actor1')
    actor2 = request.GET.get('actor2')

    if not actor1 or not actor2:
        return Response({'error': 'Les deux noms d’acteurs doivent être fournis.'}, status=400)

    movies = find_common_movies(actor1, actor2)
    return Response({'results': movies})
