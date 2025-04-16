from django.urls import path
from .views import common_movies_view, actor_autocomplete

urlpatterns = [
    path('common-movies/', common_movies_view, name='common-movies'),
    path('actor-autocomplete/', actor_autocomplete, name='actor-autocomplete'),

]