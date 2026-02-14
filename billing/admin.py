

# Register your models here.
from django.contrib import admin
from .models import (
    Subscriber, WaterRate, MeterReading,
    Bill, Ledger, OtherCharge, DisconnectionNotice
)
 
# ── Customize admin site headers ─────────────────────────────
admin.site.site_header  = 'Macrohon Water Billing'
admin.site.site_title   = 'Water Billing Admin'
admin.site.index_title  = 'Administration Dashboard'
 
 
@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display   = ['account_number', 'full_name', 'barangay',
                       'classification', 'status', 'meter_number', 'is_senior']
    list_filter    = ['classification', 'status', 'barangay', 'is_senior']
    search_fields  = ['account_number', 'last_name', 'first_name', 'meter_number']
    ordering       = ['last_name', 'first_name']
    readonly_fields = ['created_at', 'updated_at', 'get_running_balance']
    fieldsets = (
        ('Account Information', {'fields': ('account_number', 'classification', 'status', 'is_senior')}),
        ('Personal Data',       {'fields': ('last_name', 'first_name', 'middle_name', 'suffix')}),
        ('Contact & Address',   {'fields': ('address', 'barangay', 'contact_number', 'email')}),
        ('Meter Details',       {'fields': ('meter_number', 'meter_size', 'service_address')}),
        ('Dates',               {'fields': ('connection_date', 'disconnection_date')}),
        ('Financial',           {'fields': ('monthly_minimum',)}),
        ('Audit',               {'fields': ('created_by', 'created_at', 'updated_at',
                                             'get_running_balance'), 'classes': ('collapse',)}),
    )
 
 
@admin.register(WaterRate)
class WaterRateAdmin(admin.ModelAdmin):
    list_display  = ['classification', 'minimum_charge', 'minimum_volume',
                      'rate_per_cubic_m', 'effective_date', 'is_active']
    list_filter   = ['classification', 'is_active']
    ordering      = ['-effective_date']
 
 
@admin.register(MeterReading)
class MeterReadingAdmin(admin.ModelAdmin):
    list_display  = ['subscriber', 'billing_month', 'reading_date',
                      'previous_reading', 'current_reading', 'volume_consumed']
    list_filter   = ['billing_month']
    search_fields = ['subscriber__account_number', 'subscriber__last_name']
    ordering      = ['-billing_month']
 
 
@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display  = ['subscriber', 'billing_month', 'volume_consumed',
                      'basic_charge', 'penalty_amount', 'arrears',
                      'total_amount_due', 'amount_paid', 'balance', 'status']
    list_filter   = ['status', 'billing_month']
    search_fields = ['subscriber__account_number', 'subscriber__last_name']
    ordering      = ['-billing_month']
    readonly_fields = ['created_at', 'updated_at']
 
 
@admin.register(Ledger)
class LedgerAdmin(admin.ModelAdmin):
    list_display  = ['subscriber', 'entry_date', 'entry_type',
                      'description', 'debit', 'credit', 'running_balance', 'or_number']
    list_filter   = ['entry_type', 'entry_date']
    search_fields = ['subscriber__account_number', 'or_number']
 
 
@admin.register(OtherCharge)
class OtherChargeAdmin(admin.ModelAdmin):
    list_display  = ['subscriber', 'charge_type', 'description',
                      'amount', 'charge_date', 'applied_by', 'is_paid']
    list_filter   = ['charge_type', 'is_paid']
 
 
@admin.register(DisconnectionNotice)
class DisconnectionNoticeAdmin(admin.ModelAdmin):
    list_display  = ['subscriber', 'notice_date', 'cutoff_date',
                      'amount_overdue', 'status', 'issued_by']
    list_filter   = ['status']
    search_fields = ['subscriber__account_number', 'subscriber__last_name']
