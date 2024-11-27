# Generated by Django 5.0.6 on 2024-11-27 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0009_text_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='glossary',
            name='Sentence',
            field=models.CharField(default='sentence ', max_length=25),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='glossary',
            name='gloss',
            field=models.TextField(null=True),
        ),
    ]
