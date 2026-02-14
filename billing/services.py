from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from .models import WaterRate, Bill, Ledger, DisconnectionNotice
 
 
# ══════════════════════════════════════════════════════════
#   FUNCTION 1 — get_running_balance
#   Reads the ledger to find the current balance for a subscriber
# ══════════════════════════════════════════════════════════
def get_running_balance(subscriber):
    entries = subscriber.ledger_entries.all()
    debit   = entries.aggregate(Sum('debit'))['debit__sum']  or Decimal('0')
    credit  = entries.aggregate(Sum('credit'))['credit__sum'] or Decimal('0')
    return debit - credit
 
 
# ══════════════════════════════════════════════════════════
#   FUNCTION 2 — compute_water_charge
#   Calculates the water charge from the rate table
#   Args: subscriber object, volume (Decimal in cu.m)
#   Returns: Decimal charge amount
# ══════════════════════════════════════════════════════════
def compute_water_charge(subscriber, volume):
    rate = WaterRate.objects.filter(
        classification = subscriber.classification,
        is_active      = True
    ).first()
 
    if rate is None:
        raise ValueError(
            f'No active water rate found for classification: '
            f'{subscriber.get_classification_display()}. '
            f'Add a rate in the admin panel under Water Rates.'
        )
 
    volume = Decimal(str(volume))
 
#     Below or at minimum volume → apply minimum charge
    if volume <= rate.minimum_volume:
        charge = rate.minimum_charge
    else:
#         Excess volume above minimum → extra charge
        excess = volume - rate.minimum_volume
        charge = rate.minimum_charge + (excess * rate.rate_per_cubic_m)
 
#     Senior citizen discount: 20% off basic charge
    discount = Decimal('0.00')
    if subscriber.is_senior:
        discount = (charge * Decimal('0.20')).quantize(Decimal('0.01'))
        charge   = charge - discount
 
    return charge.quantize(Decimal('0.01')), discount
 
 
# ══════════════════════════════════════════════════════════
#   FUNCTION 3 — generate_bill
#   Creates a Bill record and posts it to the ledger
#   Args: subscriber, meter_reading, due_date, cutoff_date
#   Returns: Bill instance
# ══════════════════════════════════════════════════════════
def generate_bill(subscriber, meter_reading, due_date, cutoff_date, generated_by='System'):
    volume  = meter_reading.volume_consumed
    basic, discount = compute_water_charge(subscriber, volume)
 
#     Sum all unpaid/partial/overdue bills as arrears
    arrears_qs = Bill.objects.filter(
        subscriber = subscriber,
        status__in = ['UNPAID', 'PARTIAL', 'OVERDUE'],
    )
    arrears = arrears_qs.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
 
#     Sum any unpaid other charges (materials, reconnection, etc.)
    other_charges = subscriber.other_charges.filter(
        is_paid=False
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
 
    total = basic + arrears + other_charges
 
    bill = Bill.objects.create(
        subscriber       = subscriber,
        meter_reading    = meter_reading,
        billing_month    = meter_reading.billing_month,
        due_date         = due_date,
        cutoff_date      = cutoff_date,
        volume_consumed  = volume,
        basic_charge     = basic,
        senior_discount  = discount,
        other_charges    = other_charges,
        arrears          = arrears,
        total_amount_due = total,
        balance          = total,
        generated_by     = generated_by,
    )
 
#     Mark other charges as attached to this bill
    subscriber.other_charges.filter(is_paid=False).update(bill=bill)
 
#     Post billing entry to the ledger
    balance_before = get_running_balance(subscriber)
    Ledger.objects.create(
        subscriber      = subscriber,
        bill            = bill,
        entry_date      = bill.billing_month,
        entry_type      = 'BILLING',
        description     = f'Water Bill for {bill.billing_month:%B %Y}',
        debit           = total,
        running_balance = balance_before + total,
    )
 
    return bill
 
 
# ══════════════════════════════════════════════════════════
#   FUNCTION 4 — process_payment
#   Records a cash payment against a bill and posts to ledger
# ══════════════════════════════════════════════════════════
def process_payment(bill, amount_paid, or_number, received_by, remarks=''):
    amount_paid = Decimal(str(amount_paid)).quantize(Decimal('0.01'))
 
    bill.amount_paid += amount_paid
    bill.balance      = bill.total_amount_due - bill.amount_paid
 
    if bill.balance <= 0:
        bill.balance = Decimal('0.00')
        bill.status  = 'PAID'
    elif bill.amount_paid > 0:
        bill.status  = 'PARTIAL'
 
    bill.save()
 
    Ledger.objects.create(
        subscriber      = bill.subscriber,
        bill            = bill,
        entry_date      = timezone.now().date(),
        entry_type      = 'PAYMENT',
        description     = f'Payment received — OR# {or_number}',
        credit          = amount_paid,
        running_balance = get_running_balance(bill.subscriber),
        or_number       = or_number,
        received_by     = received_by,
    )
 
    return bill
 
 
# ══════════════════════════════════════════════════════════
#   FUNCTION 5 — apply_penalty
#   Applies a percentage penalty to an overdue bill
# ══════════════════════════════════════════════════════════
def apply_penalty(bill, penalty_rate_pct=Decimal('10.00')):
    if bill.status not in ['UNPAID', 'PARTIAL']:
        return None  # Only apply to unpaid/partial bills
 
    rate    = penalty_rate_pct / Decimal('100')
    penalty = (bill.balance * rate).quantize(Decimal('0.01'))
 
    bill.penalty_amount   += penalty
    bill.total_amount_due += penalty
    bill.balance          += penalty
    bill.status            = 'OVERDUE'
    bill.save()
 
    Ledger.objects.create(
        subscriber      = bill.subscriber,
        bill            = bill,
        entry_date      = timezone.now().date(),
        entry_type      = 'PENALTY',
        description     = (f'{penalty_rate_pct}% Late Penalty — '
                           f'{bill.billing_month:%B %Y}'),
        debit           = penalty,
        running_balance = get_running_balance(bill.subscriber),
    )
 
    return bill
 
 
# ══════════════════════════════════════════════════════════
#   FUNCTION 6 — issue_disconnection_notice
#   Creates a DisconnectionNotice for an overdue bill
# ══════════════════════════════════════════════════════════
def issue_disconnection_notice(bill, cutoff_date, issued_by):
    notice = DisconnectionNotice.objects.create(
        subscriber     = bill.subscriber,
        bill           = bill,
        cutoff_date    = cutoff_date,
        amount_overdue = bill.balance,
        issued_by      = issued_by,
        status         = 'PENDING',
    )
    return notice
