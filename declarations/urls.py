from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Declarations
    path('declarations/', views.declaration_list, name='declaration_list'),
    path('declarations/create/', views.declaration_create, name='declaration_create'),
    path('declarations/<int:pk>/', views.declaration_detail, name='declaration_detail'),

    # Material Products
    path('material-products/', views.material_products_list, name='material_products_list'),
    path('material-products/create/', views.material_product_create, name='material_product_create'),
    path('material-products/<int:pk>/delete/', views.material_product_delete, name='material_product_delete'),

    # Hersteller Profile
    path('hersteller-profile/', views.hersteller_profile, name='hersteller_profile'),


    # Archive
    path('archive/', views.archive_list, name='archive_list'),
    path('archive/upload/', views.archive_upload, name='archive_upload'),
    path('archive/<int:pk>/', views.archive_view, name='archive_view'),
    path('archive/<int:pk>/delete/', views.archive_delete, name='archive_delete'),

    # AJAX Endpoints
    path('api/parse-reference-pdf/', views.parse_reference_pdf, name='parse_reference_pdf'),
]
