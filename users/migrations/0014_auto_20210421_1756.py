# Generated by Django 3.1.2 on 2021-04-21 21:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_auto_20210421_1659'),
    ]

    operations = [
        migrations.AlterField(
            model_name='claimlikemodel',
            name='claim_id',
            field=models.IntegerField(default=0),
        ),
    ]
