from django.db import models
from apps.curriculum.models import TermPackage

class MpesaTransaction(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending PIN entry'),
        ('SUCCESS', 'Payment Successful'),
        ('FAILED', 'Payment Cancelled / Failed'),
    )
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    checkout_request_id = models.CharField(max_length=100, unique=True)
    merchant_request_id = models.CharField(max_length=100, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    term_package = models.ForeignKey(TermPackage, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"M-Pesa {self.mpesa_receipt_number or self.checkout_request_id} - KES {self.amount} ({self.status})"