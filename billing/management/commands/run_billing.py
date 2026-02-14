from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.models import MeterReading, Bill
from billing.services import generate_bill
from datetime import date, timedelta
 
class Command(BaseCommand):
    help = 'Generate bills for all meter readings that have no bill yet'
 
    def add_arguments(self, parser):
        parser.add_argument('--billing-month', type=str,
                            help='YYYY-MM-DD (first day of billing month)')
        parser.add_argument('--due-days',     type=int, default=15,
                            help='Days from billing month to due date (default: 15)')
        parser.add_argument('--cutoff-days',  type=int, default=20,
                            help='Days from billing month to cutoff (default: 20)')
 
    def handle(self, *args, **options):
        if options['billing_month']:
            billing_month = date.fromisoformat(options['billing_month'])
        else:
            today = date.today()
            billing_month = date(today.year, today.month, 1)
 
        due_date    = billing_month + timedelta(days=options['due_days'])
        cutoff_date = billing_month + timedelta(days=options['cutoff_days'])
 
        readings_without_bill = MeterReading.objects.filter(
            billing_month = billing_month
        ).exclude(
            id__in = Bill.objects.filter(
                billing_month=billing_month).values('meter_reading_id')
        )
 
        count = 0
        errors = 0
        for reading in readings_without_bill:
            try:
                bill = generate_bill(
                    subscriber    = reading.subscriber,
                    meter_reading = reading,
                    due_date      = due_date,
                    cutoff_date   = cutoff_date,
                    generated_by  = 'Management Command',
                )
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Bill generated: {reading.subscriber.account_number} — P{bill.total_amount_due}'
                    )
                )
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f'ERROR for {reading.subscriber}: {e}')
                )
 
        self.stdout.write(self.style.SUCCESS(
            f'Done. {count} bills generated. {errors} errors.'
        ))