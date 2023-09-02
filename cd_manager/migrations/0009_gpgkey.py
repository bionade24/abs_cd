# Generated by Django 3.2.20 on 2023-08-13 14:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cd_manager', '0008_package_makepkg_extra_args'),
    ]

    operations = [
        migrations.CreateModel(
            name='GpgKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fingerprint', models.CharField(editable=False, max_length=255, unique=True)),
                ('expiry_date', models.DateTimeField(blank=True, editable=False, null=True)),
                ('label', models.CharField(max_length=255, unique=True)),
                ('allow_sign_by_other_users', models.BooleanField(default=False)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]