from django.urls import path
from . import views

urlpatterns = [
    path('merchants/', views.MerchantListView.as_view()),
    path('merchants/<uuid:merchant_id>/', views.MerchantDetailView.as_view()),
    path('payouts/', views.PayoutCreateView.as_view()),
    path('payouts/<uuid:payout_id>/', views.PayoutDetailView.as_view()),
]