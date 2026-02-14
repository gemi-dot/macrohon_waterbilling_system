#!/usr/bin/env python
"""
Setup script to populate the water billing system with initial data.
Run this after creating your superuser account.
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'macrohon_water.settings')
django.setup()

from billing.models import WaterRate, Subscriber
from decimal import Decimal
from datetime import date

def create_water_rates():
    """Create initial water rate structure"""
    print("🔧 Creating water rate structure...")
    
    # Check if rates already exist
    if WaterRate.objects.filter(is_active=True).exists():
        print("✅ Water rates already exist")
        return WaterRate.objects.filter(is_active=True).first()
    
    # Create water rates for different classifications
    rates_data = [
        {
            'classification': 'PRIVATE',
            'minimum_charge': Decimal('150.00'),
            'minimum_volume': Decimal('10.00'),
            'rate_per_cubic_m': Decimal('15.50'),
            'effective_date': date(2026, 1, 1),
            'is_active': True,
            'approved_by': 'Water District Board',
            'sb_resolution': 'SB-2026-001'
        },
        {
            'classification': 'COMMERCIAL',
            'minimum_charge': Decimal('250.00'),
            'minimum_volume': Decimal('10.00'),
            'rate_per_cubic_m': Decimal('18.00'),
            'effective_date': date(2026, 1, 1),
            'is_active': True,
            'approved_by': 'Water District Board',
            'sb_resolution': 'SB-2026-001'
        },
        {
            'classification': 'GOVERNMENT',
            'minimum_charge': Decimal('200.00'),
            'minimum_volume': Decimal('10.00'),
            'rate_per_cubic_m': Decimal('16.00'),
            'effective_date': date(2026, 1, 1),
            'is_active': True,
            'approved_by': 'Water District Board',
            'sb_resolution': 'SB-2026-001'
        }
    ]
    
    created_rates = []
    for rate_data in rates_data:
        rate = WaterRate.objects.create(**rate_data)
        created_rates.append(rate)
        print(f"✅ Created {rate.get_classification_display()} rate:")
        print(f"   - Minimum charge: ₱{rate.minimum_charge} for {rate.minimum_volume}m³")
        print(f"   - Rate per m³: ₱{rate.rate_per_cubic_m}")
    
    return created_rates[0]

def create_sample_subscribers():
    """Create some sample subscribers"""
    print("\n👥 Creating sample subscribers...")
    
    subscribers_data = [
        {
            'account_number': 'MHN-2026-001',
            'first_name': 'Juan',
            'last_name': 'Dela Cruz',
            'address': '123 Main Street',
            'barangay': 'Poblacion',
            'contact_number': '09123456789',
            'email': 'juan.delacruz@email.com',
            'classification': 'PRIVATE',
            'status': 'ACTIVE',
            'meter_number': 'MTR001',
            'meter_size': '1/2 inch',
            'service_address': '123 Main Street, Poblacion, Macrohon',
            'connection_date': date(2025, 6, 15),
            'monthly_minimum': Decimal('150.00'),
            'is_senior': False
        },
        {
            'account_number': 'MHN-2026-002',
            'first_name': 'Maria',
            'last_name': 'Santos',
            'address': '456 Commerce Avenue',
            'barangay': 'San Isidro',
            'contact_number': '09987654321',
            'email': 'maria.santos@email.com',
            'classification': 'COMMERCIAL',
            'status': 'ACTIVE',
            'meter_number': 'MTR002',
            'meter_size': '3/4 inch',
            'service_address': '456 Commerce Avenue, San Isidro, Macrohon',
            'connection_date': date(2025, 8, 10),
            'monthly_minimum': Decimal('250.00'),
            'is_senior': False
        },
        {
            'account_number': 'MHN-2026-003',
            'first_name': 'Pedro',
            'last_name': 'Rizal',
            'middle_name': 'Garcia',
            'address': '789 Government Road',
            'barangay': 'Balamban',
            'contact_number': '09555123456',
            'email': 'pedro.rizal@email.com',
            'classification': 'PRIVATE',
            'status': 'ACTIVE',
            'meter_number': 'MTR003',
            'meter_size': '1/2 inch',
            'service_address': '789 Government Road, Balamban, Macrohon',
            'connection_date': date(2025, 9, 5),
            'monthly_minimum': Decimal('150.00'),
            'is_senior': True
        }
    ]
    
    created_count = 0
    for data in subscribers_data:
        subscriber, created = Subscriber.objects.get_or_create(
            account_number=data['account_number'],
            defaults=data
        )
        if created:
            classification = subscriber.get_classification_display()
            senior_note = " (Senior Citizen)" if subscriber.is_senior else ""
            print(f"✅ Created subscriber: {data['account_number']} - {data['first_name']} {data['last_name']}")
            print(f"   Classification: {classification}{senior_note}")
            created_count += 1
        else:
            print(f"✅ Subscriber already exists: {data['account_number']}")
    
    print(f"\n📊 Summary: {created_count} new subscribers created")
    return Subscriber.objects.all()

def main():
    print("🚀 Setting up Macrohon Water Billing System...")
    print("=" * 50)
    
    # Create water rates
    rate = create_water_rates()
    
    # Create sample subscribers
    subscribers = create_sample_subscribers()
    
    print("\n" + "=" * 50)
    print("🎉 Initial setup complete!")
    print("\nNext Steps:")
    print("1. Access admin panel at: http://127.0.0.1:8001/admin/")
    print("2. Access main dashboard at: http://127.0.0.1:8001/")
    print("3. Add meter readings for subscribers")
    print("4. Run billing command: python manage.py run_billing")
    print("\n💧 Your water billing system is ready to use!")

if __name__ == '__main__':
    main()