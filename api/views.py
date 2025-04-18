from rest_framework.decorators import api_view
from rest_framework.response import Response
from services.tmdb import find_common_movies, search_actors


@api_view(['GET'])
def actor_autocomplete(request):
    query = request.GET.get('query', '')
    results = search_actors(query)
    return Response({'results': results})


@api_view(['GET'])
def common_movies_view(request):
    actor1 = request.GET.get('actor1')
    actor2 = request.GET.get('actor2')

    if not actor1 or not actor2:
        return Response({'error': 'Les deux noms d’acteurs doivent être fournis.'}, status=400)

    movies, actor1_info, actor2_info = find_common_movies(actor1, actor2)

    return Response({
        'results': movies,
        'actor1_image': actor1_info.get('image_path'),
        'actor2_image': actor2_info.get('image_path'),
        'actor1_imdb': actor1_info.get('imdb_url'),
        'actor2_imdb': actor2_info.get('imdb_url'),
    })
