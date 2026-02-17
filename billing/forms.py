from django import forms
from .models import Subscriber, WaterRate, MeterReading, OtherCharge
 
# ──────────────────────────────────────────────────────────
#   FORM 1 — SubscriberForm
# ──────────────────────────────────────────────────────────
class SubscriberForm(forms.ModelForm):
    class Meta:
        model  = Subscriber
        fields = [
            'account_number', 'last_name', 'first_name', 'middle_name', 'suffix',
            'classification', 'status', 'is_senior',
            'address', 'barangay', 'contact_number', 'email',
            'meter_number', 'meter_size', 'service_address',
            'connection_date', 'monthly_minimum',
        ]
        widgets = {
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MHN-2026-XXX'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'suffix': forms.TextInput(attrs={'class': 'form-control'}),
            'classification': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'service_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'meter_number': forms.TextInput(attrs={'class': 'form-control'}),
            'meter_size': forms.TextInput(attrs={'class': 'form-control', 'value': '1/2 inch'}),
            'connection_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'monthly_minimum': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'value': '150.00'}),
            'is_senior': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
 
# ──────────────────────────────────────────────────────────
#   FORM 2 — MeterReadingForm
# ──────────────────────────────────────────────────────────
class MeterReadingForm(forms.ModelForm):
    class Meta:
        model  = MeterReading
        fields = ['subscriber', 'billing_month', 'reading_date',
                   'previous_reading', 'current_reading', 'reader_name', 'remarks']
        widgets = {
            'billing_month':  forms.DateInput(attrs={'type': 'date'}),
            'reading_date':   forms.DateInput(attrs={'type': 'date'}),
        }
 
    def clean(self):
        cleaned = super().clean()
        prev = cleaned.get('previous_reading')
        curr = cleaned.get('current_reading')
        subscriber = cleaned.get('subscriber')
        billing_month = cleaned.get('billing_month')
        
        # Check if current reading is less than previous reading
        if prev is not None and curr is not None and curr < prev:
            raise forms.ValidationError(
                'Current reading cannot be less than previous reading.')
        
        # Check for duplicate meter reading (subscriber + billing_month combination)
        if subscriber and billing_month:
            existing_reading = MeterReading.objects.filter(
                subscriber=subscriber,
                billing_month=billing_month
            )
            
            # If we're editing an existing reading, exclude it from the check
            if self.instance and self.instance.pk:
                existing_reading = existing_reading.exclude(pk=self.instance.pk)
            
            if existing_reading.exists():
                existing = existing_reading.first()
                raise forms.ValidationError(
                    f'A meter reading already exists for {subscriber.full_name} '
                    f'for {billing_month.strftime("%B %Y")}. '
                    f'Current reading: {existing.current_reading} m³ (taken on {existing.reading_date}). '
                    f'Please edit the existing reading instead of creating a new one.'
                )
        
        return cleaned
 
 
# ──────────────────────────────────────────────────────────
#   FORM 3 — PaymentForm
# ──────────────────────────────────────────────────────────
class PaymentForm(forms.Form):
    amount_paid = forms.DecimalField(
        max_digits=10, decimal_places=2,
        label='Amount Received (₱)',
        min_value=1,
    )
    or_number   = forms.CharField(
        max_length=50,
        label='Official Receipt Number',
    )
    received_by = forms.CharField(
        max_length=100,
        label='Received By (Cashier Name)',
    )
    remarks     = forms.CharField(
        max_length=255, required=False,
        label='Remarks (optional)',
    )
 
 
# ──────────────────────────────────────────────────────────
#   FORM 4 — OtherChargeForm
# ──────────────────────────────────────────────────────────
class OtherChargeForm(forms.ModelForm):
    class Meta:
        model  = OtherCharge
        fields = ['charge_type', 'description', 'amount', 'charge_date', 'applied_by', 'remarks']
        widgets = {
            'charge_date': forms.DateInput(attrs={'type': 'date'}),
        }
 
 
# ──────────────────────────────────────────────────────────
#   FORM 5 — BillingPeriodForm  (for running monthly billing)
# ──────────────────────────────────────────────────────────
class BillingPeriodForm(forms.Form):
    billing_month = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Billing Month (enter first day, e.g. 2025-01-01)',
    )
    due_date      = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Payment Due Date',
    )
    cutoff_date   = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Disconnection Cutoff Date',
    )

