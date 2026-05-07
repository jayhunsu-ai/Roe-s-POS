from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_add_credit_and_payment_verification'),
    ]

    operations = [
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('receiptId', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('receiptNumber', models.CharField(editable=False, max_length=20, unique=True)),
                ('format', models.CharField(choices=[('Thermal', 'Thermal Printer (80mm)'), ('A4', 'A4 Paper'), ('Mobile', 'Mobile/Digital')], default='Thermal', max_length=10)),
                ('receiptContent', models.JSONField(help_text='Structured receipt data')),
                ('receiptHTML', models.TextField(blank=True, help_text='HTML formatted receipt')),
                ('receiptText', models.TextField(blank=True, help_text='Plain text receipt for thermal printers')),
                ('printedAt', models.DateTimeField(blank=True, null=True)),
                ('printCount', models.IntegerField(default=0, help_text='Number of times receipt has been printed')),
                ('isDigitallySent', models.BooleanField(default=False, help_text='SMS/Email sent to customer')),
                ('generatedAt', models.DateTimeField(auto_now_add=True)),
                ('updatedAt', models.DateTimeField(auto_now=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='receipt', to='orders.order')),
                ('printedBy', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='receiptsPrinted', to='accounts.staff')),
            ],
            options={
                'verbose_name': 'Receipt',
                'verbose_name_plural': 'Receipts',
                'db_table': 'receipt',
                'ordering': ['-generatedAt'],
            },
        ),
    ]
