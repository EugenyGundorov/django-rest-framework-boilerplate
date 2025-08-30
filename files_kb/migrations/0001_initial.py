
from django.db import migrations, models
import django.db.models.deletion
import django_pgvector.fields

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FileAsset',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('filename', models.CharField(max_length=255)),
                ('storage_url', models.URLField(blank=True, default='', max_length=1024)),
                ('size_bytes', models.BigIntegerField(default=0)),
                ('content_type', models.CharField(blank=True, default='', max_length=100)),
                ('checksum', models.CharField(blank=True, default='', max_length=64)),
                ('source', models.CharField(blank=True, default='upload', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='KnowledgeChunk',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, default='', max_length=255)),
                ('content', models.TextField()),
                ('embedding', django_pgvector.fields.VectorField(blank=True, dimensions=1536, null=True)),
                ('meta', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('file', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chunks', to='files_kb.fileasset')),
            ],
            options={'indexes': [models.Index(fields=['created_at'], name='files_kb_kn_created_4a5e8b_idx')],},
        ),
        migrations.CreateModel(
            name='IndexJob',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('status', models.CharField(default='queued', max_length=20)),
                ('error', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('file', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='index_jobs', to='files_kb.fileasset')),
            ],
        ),
    ]
