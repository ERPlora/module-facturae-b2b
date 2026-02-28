"""Factura-e B2B URL Configuration."""

from django.urls import path
from . import views

app_name = 'facturae_b2b'

urlpatterns = [
    # Dashboard
    path('', views.index, name='dashboard'),

    # E-Invoices
    path('einvoices/', views.einvoices_list, name='einvoices'),
    path('einvoices/<uuid:pk>/', views.einvoice_detail, name='einvoice_detail'),

    # Generate
    path('generate/', views.generate_select, name='generate_select'),
    path('generate/<uuid:invoice_pk>/', views.generate_from_invoice, name='generate_from_invoice'),
    path('generate/bulk/', views.generate_bulk, name='generate_bulk'),

    # Actions
    path('einvoices/<uuid:pk>/sign/', views.einvoice_sign, name='einvoice_sign'),
    path('einvoices/<uuid:pk>/download/', views.einvoice_download, name='einvoice_download'),
    path('einvoices/<uuid:pk>/download-signed/', views.einvoice_download_signed, name='einvoice_download_signed'),
    path('einvoices/<uuid:pk>/regenerate/', views.einvoice_regenerate, name='einvoice_regenerate'),
    path('einvoices/<uuid:pk>/delete/', views.einvoice_delete, name='einvoice_delete'),
    path('einvoices/bulk/', views.einvoices_bulk_action, name='einvoices_bulk_action'),

    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/save/', views.settings_save, name='settings_save'),
    path('settings/toggle/', views.settings_toggle, name='settings_toggle'),
    path('settings/input/', views.settings_input, name='settings_input'),
    path('settings/certificate/', views.settings_certificate_upload, name='settings_certificate_upload'),
    path('settings/certificate/remove/', views.settings_certificate_remove, name='settings_certificate_remove'),
]
