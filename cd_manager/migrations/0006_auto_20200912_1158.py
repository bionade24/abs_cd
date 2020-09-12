# Generated by Django 3.1.1 on 2020-09-12 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cd_manager', '0005_auto_20200803_1038'),
    ]

    operations = [
        migrations.AlterField(
            model_name='package',
            name='build_status',
            field=models.CharField(choices=[('SUCCESS', 'Success'), ('FAILURE', 'Failure'), ('NOT_BUILT', 'Not Built'), ('BUILDING', 'Building')], default='NOT_BUILT', max_length=10),
        ),
    ]
