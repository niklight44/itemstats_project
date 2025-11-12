from django.db import models

class Item(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, db_index=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, db_index=True)
    updated_at = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = ('name', 'category')

    def __str__(self):
        return f"{self.name} ({self.category})"
