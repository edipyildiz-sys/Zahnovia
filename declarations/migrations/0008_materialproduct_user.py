# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('declarations', '0007_productwork'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialproduct',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='material_products',
                to=settings.AUTH_USER_MODEL,
                default=1  # Mevcut kayıtlar için default user
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='materialproduct',
            name='name',
            field=models.CharField(help_text='Ürün kombinasyon adı', max_length=200),
        ),
    ]
