from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='isCreditAllowed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='order',
            name='creditApprovedBy',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='creditsApproved',
                to='accounts.staff'
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='creditApprovedAt',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='verificationStatus',
            field=models.CharField(
                choices=[
                    ('Pending', 'Pending'),
                    ('Confirmed', 'Confirmed'),
                    ('Rejected', 'Rejected'),
                ],
                default='Confirmed',
                help_text='Whether the payment has been verified or is pending confirmation',
                max_length=10,
            ),
        ),
    ]
