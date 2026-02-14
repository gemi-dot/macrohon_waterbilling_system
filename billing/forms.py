from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Fieldset, HTML
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
            'connection_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}),
            'address':         forms.Textarea(attrs={'rows': 3}),
            'service_address': forms.Textarea(attrs={'rows': 3}),
        }
 
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset('Account Information',
                Row(Column('account_number',  css_class='col-md-4'),
                    Column('classification',  css_class='col-md-4'),
                    Column('status',          css_class='col-md-4')),
                Row(Column('is_senior',       css_class='col-md-12')),
            ),
            Fieldset('Personal Information',
                Row(Column('last_name',   css_class='col-md-4'),
                    Column('first_name',  css_class='col-md-4'),
                    Column('middle_name', css_class='col-md-3'),
                    Column('suffix',      css_class='col-md-1')),
            ),
            Fieldset('Contact & Location',
                Row(Column('address',        css_class='col-md-8'),
                    Column('barangay',       css_class='col-md-4')),
                Row(Column('contact_number', css_class='col-md-6'),
                    Column('email',          css_class='col-md-6')),
            ),
            Fieldset('Meter & Service',
                Row(Column('meter_number',    css_class='col-md-4'),
                    Column('meter_size',      css_class='col-md-4'),
                    Column('connection_date', css_class='col-md-4')),
                Row(Column('service_address', css_class='col-md-8'),
                    Column('monthly_minimum', css_class='col-md-4')),
            ),
            Submit('submit', 'Save Subscriber', css_class='btn btn-primary btn-lg'),
        )
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
        prev    = cleaned.get('previous_reading')
        curr    = cleaned.get('current_reading')
        if prev is not None and curr is not None and curr < prev:
            raise forms.ValidationError(
                'Current reading cannot be less than previous reading.')
        return cleaned
 
 
# ──────────────────────────────────────────────────────────
#   FORM 3 — PaymentForm
# ──────────────────────────────────────────
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

