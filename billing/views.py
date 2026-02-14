from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import date
from decimal import Decimal
 
from .models import (
    Subscriber, MeterReading, Bill,
    Ledger, OtherCharge, DisconnectionNotice
)
from .forms import (
    SubscriberForm, MeterReadingForm,
    PaymentForm, OtherChargeForm, BillingPeriodForm
)
from .services import (
    generate_bill, process_payment,
    apply_penalty, issue_disconnection_notice
)
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 1 — dashboard
# ══════════════════════════════════════════════════════════
@login_required
def dashboard(request):
    today = date.today()
    context = {
        'total_subscribers':   Subscriber.objects.count(),
        'active_subscribers':  Subscriber.objects.filter(status='ACTIVE').count(),
        'unpaid_bills':        Bill.objects.filter(status__in=['UNPAID','PARTIAL','OVERDUE']).count(),
        'overdue_bills':       Bill.objects.filter(status='OVERDUE').count(),
        'collection_today':    (Ledger.objects.filter(
                                   entry_type='PAYMENT',
                                   entry_date=today
                               ).aggregate(Sum('credit'))['credit__sum'] or Decimal('0')),
        'collection_month':    (Ledger.objects.filter(
                                   entry_type='PAYMENT',
                                   entry_date__year=today.year,
                                   entry_date__month=today.month
                               ).aggregate(Sum('credit'))['credit__sum'] or Decimal('0')),
        'recent_payments':     Ledger.objects.filter(
                                   entry_type='PAYMENT'
                               ).select_related('subscriber').order_by('-entry_date')[:10],
        'pending_notices':     DisconnectionNotice.objects.filter(
                                   status__in=['PENDING','DELIVERED']).count(),
    }
    return render(request, 'billing/dashboard.html', context)
 
 
# ══════════════════════════════════════════════════════════
#   VIEWS 2–5 — Subscriber CRUD
# ══════════════════════════════════════════════════════════
@login_required
def subscriber_list(request):
    q    = request.GET.get('q', '')
    cls  = request.GET.get('classification', '')
    stat = request.GET.get('status', '')
    qs   = Subscriber.objects.all()
 
    if q:
        qs = qs.filter(
            Q(account_number__icontains=q) |
            Q(last_name__icontains=q) |
            Q(first_name__icontains=q) |
            Q(meter_number__icontains=q)
        )
    if cls:  qs = qs.filter(classification=cls)
    if stat: qs = qs.filter(status=stat)
 
    return render(request, 'billing/subscriber_list.html', {
        'subscribers': qs,
        'q': q, 'cls': cls, 'stat': stat,
        'classification_choices': Subscriber.CLASSIFICATION_CHOICES,
        'status_choices': Subscriber.STATUS_CHOICES,
    })
 
 
@login_required
def subscriber_create(request):
    form = SubscriberForm(request.POST or None)
    if form.is_valid():
        sub = form.save(commit=False)
        sub.created_by = request.user
        sub.save()
        messages.success(request, f'Subscriber {sub.account_number} created successfully.')
        return redirect('subscriber-detail', pk=sub.pk)
    return render(request, 'billing/subscriber_form.html', {'form': form, 'title': 'Add Subscriber'})
 
 
@login_required
def subscriber_detail(request, pk):
    sub      = get_object_or_404(Subscriber, pk=pk)
    bills    = sub.bills.all().order_by('-billing_month')
    ledger   = sub.ledger_entries.all().order_by('entry_date', 'created_at')
    notices  = sub.disconnection_notices.all().order_by('-notice_date')
    balance  = sub.get_running_balance()
    return render(request, 'billing/subscriber_detail.html', {
        'sub': sub, 'bills': bills, 'ledger': ledger,
        'notices': notices, 'balance': balance,
    })
 
 
@login_required
def subscriber_edit(request, pk):
    sub  = get_object_or_404(Subscriber, pk=pk)
    form = SubscriberForm(request.POST or None, instance=sub)
    if form.is_valid():
        form.save()
        messages.success(request, 'Subscriber updated successfully.')
        return redirect('subscriber-detail', pk=sub.pk)
    return render(request, 'billing/subscriber_form.html', {'form': form, 'title': 'Edit Subscriber', 'sub': sub})
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 6 — Meter Reading (record field reading)
# ══════════════════════════════════════════════════════════
@login_required
def reading_create(request, subscriber_pk):
    sub  = get_object_or_404(Subscriber, pk=subscriber_pk)
    form = MeterReadingForm(request.POST or None, initial={'subscriber': sub})
 
    if form.is_valid():
        reading = form.save()
        messages.success(request, f'Reading saved: {reading.volume_consumed} cu.m consumed.')
        return redirect('generate-bill', reading_pk=reading.pk)
 
    return render(request, 'billing/reading_form.html', {'form': form, 'sub': sub})
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 7 — Generate Bill from a meter reading
# ══════════════════════════════════════════════════════════
@login_required
def generate_bill_view(request, reading_pk):
    reading = get_object_or_404(MeterReading, pk=reading_pk)
 
    if hasattr(reading, 'bill'):
        messages.warning(request, 'A bill already exists for this reading.')
        return redirect('bill-detail', pk=reading.bill.pk)
 
    form = BillingPeriodForm(request.POST or None)
    if form.is_valid():
        try:
            bill = generate_bill(
                subscriber    = reading.subscriber,
                meter_reading = reading,
                due_date      = form.cleaned_data['due_date'],
                cutoff_date   = form.cleaned_data['cutoff_date'],
                generated_by  = request.user.get_full_name() or request.user.username,
            )
            messages.success(request, f'Bill generated: P{bill.total_amount_due}')
            return redirect('bill-detail', pk=bill.pk)
        except ValueError as e:
            messages.error(request, str(e))
 
    return render(request, 'billing/generate_bill.html', {'form': form, 'reading': reading})
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 8 — Bill List
# ══════════════════════════════════════════════════════════
@login_required
def bill_list(request):
    month  = request.GET.get('month', '')
    status = request.GET.get('status', '')
    qs     = Bill.objects.select_related('subscriber').all()
 
    if month:
        y, m  = map(int, month.split('-'))
        qs    = qs.filter(billing_month__year=y, billing_month__month=m)
    if status:
        qs    = qs.filter(status=status)
 
    totals = qs.aggregate(
        total_due=Sum('total_amount_due'),
        total_paid=Sum('amount_paid'),
        total_balance=Sum('balance'),
    )
    return render(request, 'billing/bill_list.html', {
        'bills': qs.order_by('-billing_month'),
        'totals': totals, 'month': month, 'status': status,
        'status_choices': Bill.STATUS_CHOICES,
    })
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 9 — Bill Detail
# ══════════════════════════════════════════════════════════
@login_required
def bill_detail(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    return render(request, 'billing/bill_detail.html', {'bill': bill})
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 10 — Record Payment
# ══════════════════════════════════════════════════════════
@login_required
def record_payment(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    form = PaymentForm(request.POST or None)
 
    if form.is_valid():
        process_payment(
            bill        = bill,
            amount_paid = form.cleaned_data['amount_paid'],
            or_number   = form.cleaned_data['or_number'],
            received_by = form.cleaned_data['received_by'],
        )
        messages.success(request, f'Payment of P{form.cleaned_data["amount_paid"]} recorded.')
        return redirect('bill-detail', pk=bill.pk)
 
    return render(request, 'billing/payment_form.html', {'form': form, 'bill': bill})
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 11 — Print Billing Notice (HTML printable page)
# ══════════════════════════════════════════════════════════
@login_required
def print_billing_notice(request, pk):
    bill   = get_object_or_404(Bill, pk=pk)
    notice = bill.disconnection_notices.filter(
        status__in=['PENDING','DELIVERED']).first()
    return render(request, 'billing/billing_notice.html', {
        'bill': bill, 'notice': notice,
    })
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 12 — Issue Disconnection Notice
# ══════════════════════════════════════════════════════════
@login_required
def issue_notice(request, bill_pk):
    bill = get_object_or_404(Bill, pk=bill_pk)
    if request.method == 'POST':
        cutoff_date = request.POST.get('cutoff_date')
        notice = issue_disconnection_notice(
            bill        = bill,
            cutoff_date = cutoff_date,
            issued_by   = request.user.get_full_name() or request.user.username,
        )
        messages.success(request, f'Disconnection notice issued. Cutoff: {notice.cutoff_date}')
        return redirect('print-billing-notice', pk=bill.pk)
    return render(request, 'billing/issue_notice.html', {'bill': bill})
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 13 — Subscriber Ledger
# ══════════════════════════════════════════════════════════
@login_required
def subscriber_ledger(request, pk):
    sub     = get_object_or_404(Subscriber, pk=pk)
    entries = sub.ledger_entries.all().order_by('entry_date', 'created_at')
    balance = sub.get_running_balance()
    return render(request, 'billing/ledger.html', {
        'sub': sub, 'entries': entries, 'balance': balance,
    })
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 14 — Collection Report
# ══════════════════════════════════════════════════════════
@login_required
def collection_report(request):
    today  = date.today()
    month  = request.GET.get('month', today.strftime('%Y-%m'))
    y, m   = map(int, month.split('-'))
 
    payments = Ledger.objects.filter(
        entry_type       = 'PAYMENT',
        entry_date__year = y,
        entry_date__month= m,
    ).select_related('subscriber').order_by('entry_date')
 
    summary = payments.aggregate(
        total = Sum('credit'),
        count = Count('id'),
    )
 
    by_day = payments.values('entry_date').annotate(
        daily_total = Sum('credit'),
        daily_count = Count('id'),
    ).order_by('entry_date')
 
    by_class = payments.values('subscriber__classification').annotate(
        class_total = Sum('credit'),
        class_count = Count('id'),
    )
 
    return render(request, 'billing/collection_report.html', {
        'payments': payments,
        'summary':  summary,
        'by_day':   by_day,
        'by_class': by_class,
        'month':    month,
    })
 
 
# ══════════════════════════════════════════════════════════
#   VIEW 15 — Delinquent Accounts Report
# ══════════════════════════════════════════════════════════
@login_required
def delinquent_report(request):
    overdue = Bill.objects.filter(
        status__in=['UNPAID','PARTIAL','OVERDUE']
    ).select_related('subscriber').order_by('-balance')
 
    total_overdue = overdue.aggregate(Sum('balance'))['balance__sum'] or Decimal('0')
 
    return render(request, 'billing/delinquent_report.html', {
        'bills':         overdue,
        'total_overdue': total_overdue,
        'count':         overdue.count(),
    })
