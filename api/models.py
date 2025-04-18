from django.db import models

class ActorPair(models.Model):
    actor1_id = models.IntegerField()
    actor2_id = models.IntegerField()
    actor1_name = models.CharField(max_length=255)
    actor2_name = models.CharField(max_length=255)
    common_movies_count = models.PositiveIntegerField()
    common_movies = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('actor1_id', 'actor2_id')

    def __str__(self):
        return f"{self.actor1_name} & {self.actor2_name} ({self.common_movies_count} films)"

