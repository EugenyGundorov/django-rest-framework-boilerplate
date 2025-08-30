
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('chatgpt', '0001_initial'),
    ]

    operations = [
        migrations.AddField(model_name='gptrequest', name='gpt_key', field=models.CharField(blank=True, default='', max_length=200)),
        migrations.AddField(model_name='gptrequest', name='agent_key', field=models.CharField(blank=True, default='', max_length=200)),
        migrations.AddField(model_name='gptrequest', name='message_size', field=models.IntegerField(default=2048)),
        migrations.AddField(model_name='gptrequest', name='assyst_promt', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='gptrequest', name='use_agent', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='gptrequest', name='files', field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name='gptrequest', name='knowledge', field=models.JSONField(blank=True, default=list)),
        migrations.AlterField(model_name='gptrequest', name='gpt_api', field=models.CharField(default='openai', max_length=100)),
        migrations.AlterField(model_name='gptrequest', name='model', field=models.CharField(blank=True, default='gpt-4o-mini', max_length=100)),
    ]
