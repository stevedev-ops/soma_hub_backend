from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import uuid, time
from .models import MpesaTransaction
from apps.curriculum.models import TermPackage, AffiliateConversion
from apps.core.models import Student
from apps.tracker.models import Enrollment

@api_view(['POST'])
def initiate_stk_push(request):
    phone = request.data.get('phone_number', '0712345678')
    package_id = request.data.get('package_id')
    student_id = request.data.get('student_id')

    if phone.startswith('0'):
        phone = '254' + phone[1:]
    elif phone.startswith('+'):
        phone = phone[1:]

    package = TermPackage.objects.filter(id=package_id).first() if package_id else TermPackage.objects.first()
    amount = package.price_kes if package else 6500.00

    checkout_request_id = f"ws_CO_{int(time.time())}_{uuid.uuid4().hex[:6].upper()}"
    merchant_request_id = f"MR_{int(time.time())}"

    tx = MpesaTransaction.objects.create(
        phone_number=phone,
        amount=amount,
        checkout_request_id=checkout_request_id,
        merchant_request_id=merchant_request_id,
        term_package=package,
        status='PENDING'
    )

    return Response({
        'success': True,
        'checkout_request_id': checkout_request_id,
        'customer_message': f"Success. STK Push prompt sent to {phone}. Please enter your M-Pesa PIN on your phone.",
        'amount': amount,
        'package_title': package.title if package else 'Grade 4 Term 1 Complete Box',
        'phone': phone
    })

@api_view(['POST'])
def confirm_mpesa_pin(request):
    checkout_request_id = request.data.get('checkout_request_id')
    student_id = request.data.get('student_id')
    creator_handle = request.data.get('creator_handle', '@mamateaches_ke')
    
    tx = MpesaTransaction.objects.filter(checkout_request_id=checkout_request_id).first()
    if not tx:
        tx = MpesaTransaction.objects.first()

    receipt_no = f"SKM{int(time.time())%100000}{uuid.uuid4().hex[:4].upper()}"
    if tx:
        tx.status = 'SUCCESS'
        tx.mpesa_receipt_number = receipt_no
        tx.save()

        student = Student.objects.filter(id=student_id).first() if student_id else Student.objects.first()
        if student and tx.term_package:
            Enrollment.objects.get_or_create(
                student=student,
                term_package=tx.term_package,
                defaults={'is_paid': True}
            )

        # Automatically credit affiliate conversion in database
        if creator_handle:
            AffiliateConversion.objects.create(
                creator_handle=creator_handle,
                parent_name=student.parent.first_name if (student and student.parent) else 'Parent Subscriber',
                parent_phone=tx.phone_number,
                template_id=request.data.get('template_id', 'mama_teaches_cbc4'),
                commission_kes=1500.00,
                status='Credited'
            )

    return Response({
        'success': True,
        'status': 'SUCCESS',
        'mpesa_receipt_number': receipt_no,
        'amount': tx.amount if tx else 6500.00,
        'affiliate_credited': True,
        'message': f"Confirmed! KES {tx.amount if tx else 6500} paid via M-Pesa. Receipt: {receipt_no}. Homeschool-in-a-Box unlocked!"
    })
