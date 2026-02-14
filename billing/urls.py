from django.urls import path
from . import views
 
urlpatterns = [
 
#     ── Dashboard ─────────────────────────────────────────
    path('',                                views.dashboard,              name='dashboard'),
 
#     ── Subscribers ───────────────────────────────────────
    path('subscribers/',                    views.subscriber_list,        name='subscriber-list'),
    path('subscribers/add/',                views.subscriber_create,      name='subscriber-create'),
    path('subscribers/<int:pk>/',           views.subscriber_detail,      name='subscriber-detail'),
    path("subscriber/<int:pk>/", views.subscriber_detail, name="subscriber_detail"),

    path('subscribers/<int:pk>/edit/',      views.subscriber_edit,        name='subscriber-edit'),
    path('subscribers/<int:pk>/ledger/',    views.subscriber_ledger,      name='subscriber-ledger'),
 
#     ── Meter Readings ────────────────────────────────────
    path('readings/<int:subscriber_pk>/add/',  views.reading_create,     name='reading-create'),
 
#     ── Bills ─────────────────────────────────────────────
    path('bills/',                          views.bill_list,              name='bill-list'),
    path('bills/<int:pk>/',                 views.bill_detail,            name='bill-detail'),
    path('bills/generate/<int:reading_pk>/',views.generate_bill_view,    name='generate-bill'),
    path('bills/<int:pk>/pay/',             views.record_payment,         name='record-payment'),
    path('bills/<int:pk>/notice/print/',    views.print_billing_notice,   name='print-billing-notice'),
    path('bills/<int:bill_pk>/notice/issue/',views.issue_notice,          name='issue-notice'),
 
#     ── Reports ───────────────────────────────────────────
    path('reports/collection/',             views.collection_report,      name='collection-report'),
    path('reports/delinquent/',             views.delinquent_report,      name='delinquent-report'),
]
