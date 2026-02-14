# Create your models here.
from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.models import User
 
 
# ═══════════════════════════════════════════════════════════
#   MODEL 1 — Subscriber  (central account holder record)
# ═══════════════════════════════════════════════════════════
class Subscriber(models.Model):
    CLASSIFICATION_CHOICES = [
        ('PRIVATE',    'Private / Residential'),
        ('COMMERCIAL', 'Commercial / Business'),
        ('GOVERNMENT', 'Government Institution'),
        ('BULK',       'Bulk / Reseller'),
    ]
    STATUS_CHOICES = [
        ('ACTIVE',       'Active'),
        ('DISCONNECTED', 'Disconnected'),
        ('SUSPENDED',    'Suspended'),
        ('CLOSED',       'Closed'),
    ]
 
#     ── Identity ──────────────────────────────────────────────
    account_number  = models.CharField(max_length=20, unique=True,
                          help_text='Format: MHN-YYYY-NNNN')
    last_name       = models.CharField(max_length=100)
    first_name      = models.CharField(max_length=100)
    middle_name     = models.CharField(max_length=100, blank=True)
    suffix          = models.CharField(max_length=10, blank=True,
                          help_text='Jr., Sr., III, etc.')
 
#     ── Contact & Location ────────────────────────────────────
    address         = models.TextField()
    barangay        = models.CharField(max_length=100)
    contact_number  = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
 
#     ── Account Classification ────────────────────────────────
    classification  = models.CharField(max_length=20,
                          choices=CLASSIFICATION_CHOICES,
                          default='PRIVATE')
    status          = models.CharField(max_length=20,
                          choices=STATUS_CHOICES,
                          default='ACTIVE')
 
#     ── Meter Information ─────────────────────────────────────
    meter_number    = models.CharField(max_length=50, unique=True)
    meter_size      = models.CharField(max_length=20, default='1/2 inch')
    service_address = models.TextField()
 
#     ── Account Dates ─────────────────────────────────────────
    connection_date = models.DateField()
    disconnection_date = models.DateField(null=True, blank=True)
 
#     ── Financial Settings ────────────────────────────────────
    monthly_minimum = models.DecimalField(max_digits=10,
                          decimal_places=2, default=Decimal('0.00'))
    is_senior       = models.BooleanField(default=False,
                          help_text='Senior Citizen — 20% discount applies')
 #     ── Audit ─────────────────────────────────────────────────
    created_by      = models.ForeignKey(User, on_delete=models.SET_NULL,
                          null=True, blank=True, related_name='created_subscribers')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name        = 'Subscriber'
        verbose_name_plural = 'Subscribers'
 
    def __str__(self):
        return f'{self.account_number} - {self.last_name}, {self.first_name}'
 
    def full_name(self):
        parts = [self.last_name, ',', self.first_name, self.middle_name]
        return ' '.join(p for p in parts if p).strip()
 
    def get_running_balance(self):
        from django.db.models import Sum
        entries = self.ledger_entries.all()
        debit   = entries.aggregate(Sum('debit')) ['debit__sum']  or Decimal('0')
        credit  = entries.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
        return debit - credit
 
 
# ═══════════════════════════════════════════════════════════
#   MODEL 2 — WaterRate  (tariff schedule)
# ═══════════════════════════════════════════════════════════
class WaterRate(models.Model):
    classification    = models.CharField(max_length=20,
                            choices=Subscriber.CLASSIFICATION_CHOICES)
    minimum_charge    = models.DecimalField(max_digits=10, decimal_places=2,
                            help_text='Flat charge for minimum volume')
    minimum_volume    = models.DecimalField(max_digits=10, decimal_places=2,
                            default=10, help_text='Cu.m included in minimum charge')
    rate_per_cubic_m  = models.DecimalField(max_digits=10, decimal_places=4,
                            help_text='Rate per cu.m ABOVE minimum')
    effective_date    = models.DateField()
    is_active         = models.BooleanField(default=True)
    approved_by       = models.CharField(max_length=100, blank=True)
    sb_resolution     = models.CharField(max_length=50, blank=True,
                            help_text='Sangguniang Bayan Resolution No.')
 
    class Meta:
        ordering = ['-effective_date']
 
    def __str__(self):
        return (f'{self.get_classification_display()} | '
                f'Min: P{self.minimum_charge} | '
                f'P{self.rate_per_cubic_m}/cu.m')
 
 
# ═══════════════════════════════════════════════════════════
#   MODEL 3 — MeterReading  (monthly field reading)
# ═══════════════════════════════════════════════════════════
class MeterReading(models.Model):
    subscriber       = models.ForeignKey(Subscriber,
                           on_delete=models.CASCADE,
                           related_name='meter_readings')
    billing_month    = models.DateField(
                           help_text='First day of the billing month, e.g. 2025-01-01')
    reading_date     = models.DateField(default=timezone.now)
    previous_reading = models.DecimalField(max_digits=12, decimal_places=2)
    current_reading  = models.DecimalField(max_digits=12, decimal_places=2)
    reader_name      = models.CharField(max_length=100, blank=True)
    remarks          = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-billing_month']
        unique_together = ['subscriber', 'billing_month']
 
    @property
    def volume_consumed(self):
        """Returns cubic meters consumed this month."""
        return self.current_reading - self.previous_reading
 
    def __str__(self):
        return (f'{self.subscriber.account_number} | '
                f'{self.billing_month:%B %Y} | '
                f'{self.volume_consumed} cu.m')
 
 
# ═══════════════════════════════════════════════════════════
#   MODEL 4 — Bill  (monthly statement of account)
# ═══════════════════════════════════════════════════════════
class Bill(models.Model):
    STATUS_CHOICES = [
        ('UNPAID',     'Unpaid'),
        ('PARTIAL',    'Partially Paid'),
        ('PAID',       'Paid in Full'),
        ('OVERDUE',    'Overdue / With Penalty'),
        ('WRITTEN_OFF','Written Off'),
    ]
 
    subscriber       = models.ForeignKey(Subscriber,
                           on_delete=models.CASCADE, related_name='bills')
    meter_reading    = models.OneToOneField(MeterReading,
                           on_delete=models.CASCADE, related_name='bill')
    billing_month    = models.DateField()
    due_date         = models.DateField()
    cutoff_date      = models.DateField()
 
#     ── Charge Breakdown ──────────────────────────────────────
    volume_consumed  = models.DecimalField(max_digits=10, decimal_places=2)
    basic_charge     = models.DecimalField(max_digits=10, decimal_places=2,
                           help_text='Water charge from rate table')
    senior_discount  = models.DecimalField(max_digits=10, decimal_places=2,
                           default=Decimal('0.00'))
    other_charges    = models.DecimalField(max_digits=10, decimal_places=2,
                           default=Decimal('0.00'))
    penalty_amount   = models.DecimalField(max_digits=10, decimal_places=2,
                           default=Decimal('0.00'))
    arrears          = models.DecimalField(max_digits=10, decimal_places=2,
                           default=Decimal('0.00'),
                           help_text='Unpaid balance carried from previous bills')
#     ── Totals & Payment ──────────────────────────────────────
    total_amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid      = models.DecimalField(max_digits=10, decimal_places=2,
                           default=Decimal('0.00'))
    balance          = models.DecimalField(max_digits=10, decimal_places=2,
                           default=Decimal('0.00'))
    status           = models.CharField(max_length=20,
                           choices=STATUS_CHOICES, default='UNPAID')
 
#     ── Audit ─────────────────────────────────────────────────
    generated_by     = models.CharField(max_length=100)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)
 
    class Meta:
        ordering = ['-billing_month']
 
    def __str__(self):
        return (f'Bill {self.subscriber.account_number} | '
                f'{self.billing_month:%B %Y} | '
                f'P{self.total_amount_due}')
 
    def recompute_balance(self):
        self.balance = self.total_amount_due - self.amount_paid
        if   self.balance <= 0:         self.status = 'PAID'
        elif self.amount_paid > 0:      self.status = 'PARTIAL'
        self.save(update_fields=['balance', 'status', 'updated_at'])
 
# ═══════════════════════════════════════════════════════════
#   MODEL 5 — Ledger  (running debit/credit per subscriber)
# ═══════════════════════════════════════════════════════════
class Ledger(models.Model):
    ENTRY_TYPE_CHOICES = [
        ('BILLING',      'Monthly Billing'),
        ('PAYMENT',      'Payment Received'),
        ('PENALTY',      'Penalty Charge'),
        ('ADJUSTMENT',   'Adjustment'),
        ('RECONNECTION', 'Reconnection Fee'),
        ('MATERIAL',     'Materials / Labor'),
        ('DISCOUNT',     'Discount Applied'),
        ('OTHER',        'Other Charge'),
    ]
 
    subscriber      = models.ForeignKey(Subscriber,
                          on_delete=models.CASCADE,
                          related_name='ledger_entries')
    bill            = models.ForeignKey(Bill,
                          on_delete=models.SET_NULL,
                          null=True, blank=True,
                          related_name='ledger_entries')
    entry_date      = models.DateField()
    entry_type      = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES)
    description     = models.TextField()
    debit           = models.DecimalField(max_digits=10, decimal_places=2,
                          default=Decimal('0.00'))
    credit          = models.DecimalField(max_digits=10, decimal_places=2,
                          default=Decimal('0.00'))
    running_balance = models.DecimalField(max_digits=10, decimal_places=2,
                          default=Decimal('0.00'))

#     ── Payment Info (for PAYMENT entries) ───────────────────
    or_number       = models.CharField(max_length=50, blank=True,
                          help_text='Official Receipt Number')
    received_by     = models.CharField(max_length=100, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['entry_date', 'created_at']
 
    def __str__(self):
        return (f'{self.subscriber.account_number} | '
                f'{self.get_entry_type_display()} | '
                f'DR:{self.debit}  CR:{self.credit}')
 
 
# ═══════════════════════════════════════════════════════════
#   MODEL 6 — OtherCharge  (penalty, reconnect, materials)
# ═══════════════════════════════════════════════════════════
class OtherCharge(models.Model):
    CHARGE_TYPE_CHOICES = [
        ('PENALTY',      'Late Payment Penalty'),
        ('RECONNECTION', 'Reconnection Fee'),
        ('MATERIAL',     'Materials Charge'),
        ('LABOR',        'Labor Charge'),
        ('METER_REPL',   'Meter Replacement'),
        ('CUSTOM',       'Custom / Other'),
    ]
 
    subscriber   = models.ForeignKey(Subscriber, on_delete=models.CASCADE,
                       related_name='other_charges')
    bill         = models.ForeignKey(Bill, on_delete=models.SET_NULL,
                       null=True, blank=True, related_name='other_charge_items')
    charge_type  = models.CharField(max_length=20, choices=CHARGE_TYPE_CHOICES)
    description  = models.CharField(max_length=255)
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    charge_date  = models.DateField(default=timezone.now)
    applied_by   = models.CharField(max_length=100)
    is_paid      = models.BooleanField(default=False)
    remarks      = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f'{self.subscriber.account_number} | {self.get_charge_type_display()} | P{self.amount}'
# ═══════════════════════════════════════════════════════════
#   MODEL 7 — DisconnectionNotice  (cutoff / disconnection)
# ═══════════════════════════════════════════════════════════
class DisconnectionNotice(models.Model):
    STATUS_CHOICES = [
        ('PENDING',      'Notice Pending Delivery'),
        ('DELIVERED',    'Notice Delivered'),
        ('DISCONNECTED', 'Service Disconnected'),
        ('RECONNECTED',  'Service Reconnected'),
        ('CANCELLED',    'Notice Cancelled'),
    ]
 
    subscriber       = models.ForeignKey(Subscriber,
                           on_delete=models.CASCADE,
                           related_name='disconnection_notices')
    bill             = models.ForeignKey(Bill, on_delete=models.CASCADE,
                           related_name='disconnection_notices')
    notice_date      = models.DateField(auto_now_add=True)
    cutoff_date      = models.DateField()
    amount_overdue   = models.DecimalField(max_digits=10, decimal_places=2)
    penalty_rate_pct = models.DecimalField(max_digits=5, decimal_places=2,
                           default=Decimal('10.00'),
                           help_text='Penalty rate in percent, e.g. 10.00 = 10%')
    reconnection_fee = models.DecimalField(max_digits=10, decimal_places=2,
                           default=Decimal('500.00'))
    status           = models.CharField(max_length=20,
                           choices=STATUS_CHOICES, default='PENDING')
    issued_by        = models.CharField(max_length=100)
    remarks          = models.TextField(blank=True)
    disconnected_at  = models.DateTimeField(null=True, blank=True)
    reconnected_at   = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-notice_date']
 
    def __str__(self):
        return (f'Notice | {self.subscriber.account_number} | '
                f'Cutoff: {self.cutoff_date} | {self.get_status_display()}')