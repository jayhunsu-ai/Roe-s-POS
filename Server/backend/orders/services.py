# orders/services.py
from datetime import datetime
from django.utils import timezone
from django.conf import settings


class ReceiptService:

    @staticmethod
    def generate_receipt(order, format='Thermal'):
        from .models import Receipt

        # Build content dict BEFORE creating the Receipt so
        # receiptNumber is available to format into the text/html.
        # Bug Fix #13 — original code put '' as receiptNumber in the dict,
        # saved the Receipt, got the auto-generated number, but never
        # patched it back into receiptContent or the text/html.
        receipt_data = {
            'orderNumber':   order.orderNumber,
            'orderType':     order.get_orderType_display(),
            'timestamp':     timezone.now().isoformat(),
            'businessName':  getattr(settings, 'BUSINESS_NAME', 'Roe\'s Restaurant'),
            'businessPhone': getattr(settings, 'BUSINESS_PHONE', ''),
            'businessAddress': getattr(settings, 'BUSINESS_ADDRESS', ''),
            'customerInfo': {
                'name':        order.customerName or 'Walk-in Customer',
                'phone':       order.customerPhone or '',
                'tableNumber': order.tableNumber or '',
            },
            'items':       [],
            'subtotal':    float(order.subtotal),
            'discount':    float(order.discountAmount),
            'tax':         float(order.taxAmount),
            'total':       float(order.totalAmount),
            'paymentInfo': [],
            'notes':       order.note or '',
            'staff':       order.takenBy.staffName if order.takenBy else 'Unknown',
        }

        for item in order.items.all():
            item_data = {
                'name':      item.menuItem.name,
                'quantity':  item.quantity,
                'unitPrice': float(item.unitPrice),
                'lineTotal': float(item.lineTotal),
                'note':      item.note or '',
            }
            if item.selectedAddons.exists():
                item_data['addons'] = [
                    {'name': a.addon.name, 'price': float(a.extraPrice)}
                    for a in item.selectedAddons.all()
                ]
            receipt_data['items'].append(item_data)

        for payment in order.payments.all():
            receipt_data['paymentInfo'].append({
                'method':    payment.get_method_display(),
                'amount':    float(payment.amountPaid),
                'change':    float(payment.amountChange),
                'reference': payment.reference or '',
            })

        # Save the Receipt row — auto-generates receiptNumber in Receipt.save()
        receipt = Receipt.objects.create(
            order          = order,
            format         = format,
            receiptContent = receipt_data,
        )

        # ── Bug Fix #13: patch real receiptNumber back in everywhere ──────
        receipt_data['receiptNumber'] = receipt.receiptNumber
        receipt.receiptContent        = receipt_data   # update JSON field too

        if format == 'Thermal':
            receipt.receiptText = ReceiptService.format_thermal_receipt(receipt_data)
        elif format == 'A4':
            receipt.receiptHTML = ReceiptService.format_html_receipt(receipt_data)

        receipt.save(update_fields=['receiptContent', 'receiptText', 'receiptHTML'])
        return receipt

    @staticmethod
    def format_thermal_receipt(receipt_data):
        lines = []
        business = receipt_data['businessName']

        lines.append('=' * 40)
        lines.append(f"{business:^40}")
        lines.append('=' * 40)

        if receipt_data['businessPhone']:
            lines.append(f"Tel: {receipt_data['businessPhone']}")
        if receipt_data['businessAddress']:
            lines.append(f"Addr: {receipt_data['businessAddress']}")

        lines.append('-' * 40)
        lines.append(f"Receipt #: {receipt_data['receiptNumber']}")
        lines.append(f"Order #:   {receipt_data['orderNumber']}")
        lines.append(f"Type:      {receipt_data['orderType']}")
        lines.append(f"Date:      {receipt_data['timestamp']}")
        lines.append(f"Staff:     {receipt_data['staff']}")
        lines.append('-' * 40)

        lines.append(f"Customer: {receipt_data['customerInfo']['name']}")
        if receipt_data['customerInfo']['phone']:
            lines.append(f"Phone:    {receipt_data['customerInfo']['phone']}")
        if receipt_data['customerInfo']['tableNumber']:
            lines.append(f"Table:    {receipt_data['customerInfo']['tableNumber']}")

        lines.append('-' * 40)
        lines.append(f"{'Item':<20} {'Qty':>5} {'Total':>8}")
        lines.append('-' * 40)

        for item in receipt_data['items']:
            lines.append(
                f"{item['name']:<20} {item['quantity']:>5} "
                f"₦{item['lineTotal']:>7.2f}"
            )
            lines.append(f"  Unit: ₦{item['unitPrice']:.2f}")
            for addon in item.get('addons', []):
                lines.append(f"  + {addon['name']}: ₦{addon['price']:.2f}")
            if item['note']:
                lines.append(f"  Note: {item['note']}")

        lines.append('-' * 40)
        lines.append(f"{'Subtotal:':>32} ₦{receipt_data['subtotal']:>7.2f}")
        if receipt_data['discount'] > 0:
            lines.append(f"{'Discount:':>32} -₦{receipt_data['discount']:>6.2f}")
        if receipt_data['tax'] > 0:
            lines.append(f"{'Tax:':>32} ₦{receipt_data['tax']:>7.2f}")
        lines.append('=' * 40)
        lines.append(f"{'TOTAL:':>32} ₦{receipt_data['total']:>7.2f}")
        lines.append('=' * 40)

        lines.append("Payment:")
        for p in receipt_data['paymentInfo']:
            lines.append(f"  {p['method']}: ₦{p['amount']:.2f}")
            if p['change'] > 0:
                lines.append(f"  Change: ₦{p['change']:.2f}")
            if p['reference']:
                lines.append(f"  Ref: {p['reference']}")

        lines.append('-' * 40)
        if receipt_data['notes']:
            lines.append(f"Notes: {receipt_data['notes']}")

        lines.append('')
        lines.append("Thank you for your patronage!".center(40))
        lines.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^40}")
        lines.append('=' * 40)
        return '\n'.join(lines)

    @staticmethod
    def format_html_receipt(receipt_data):
        items_html = ''
        for item in receipt_data['items']:
            items_html += f"""
            <tr>
                <td>{item['name']}</td>
                <td style="text-align:right">{item['quantity']}</td>
                <td style="text-align:right">₦{item['unitPrice']:.2f}</td>
                <td style="text-align:right">₦{item['lineTotal']:.2f}</td>
            </tr>"""
            for addon in item.get('addons', []):
                items_html += f"""
            <tr>
                <td style="padding-left:20px">+ {addon['name']}</td>
                <td></td><td></td>
                <td style="text-align:right">₦{addon['price']:.2f}</td>
            </tr>"""

        discount_row = (
            f'<div><strong>Discount:</strong> -₦{receipt_data["discount"]:.2f}</div>'
            if receipt_data['discount'] > 0 else ''
        )
        tax_row = (
            f'<div><strong>Tax:</strong> ₦{receipt_data["tax"]:.2f}</div>'
            if receipt_data['tax'] > 0 else ''
        )

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Receipt {receipt_data['receiptNumber']}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    .receipt {{ max-width: 600px; margin: 0 auto; border: 1px solid #ccc; padding: 20px; }}
    .header {{ text-align: center; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    th {{ background: #f5f5f5; padding: 8px; border-bottom: 2px solid #333; text-align: left; }}
    td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
    .total-row {{ font-weight: bold; font-size: 18px; border-top: 2px solid #333; padding-top: 10px; }}
    .footer {{ text-align: center; margin-top: 20px; color: #666; }}
  </style>
</head>
<body>
  <div class="receipt">
    <div class="header">
      <h1>{receipt_data['businessName']}</h1>
      <p>{receipt_data['businessPhone']}</p>
      <p>{receipt_data['businessAddress']}</p>
    </div>
    <p><strong>Receipt #:</strong> {receipt_data['receiptNumber']}</p>
    <p><strong>Order #:</strong>   {receipt_data['orderNumber']}</p>
    <p><strong>Date:</strong>      {receipt_data['timestamp']}</p>
    <p><strong>Staff:</strong>     {receipt_data['staff']}</p>
    <p><strong>Customer:</strong>  {receipt_data['customerInfo']['name']}</p>
    <table>
      <thead>
        <tr>
          <th>Item</th><th style="text-align:right">Qty</th>
          <th style="text-align:right">Unit</th><th style="text-align:right">Total</th>
        </tr>
      </thead>
      <tbody>{items_html}</tbody>
    </table>
    <div style="text-align:right">
      <div><strong>Subtotal:</strong> ₦{receipt_data['subtotal']:.2f}</div>
      {discount_row}
      {tax_row}
      <div class="total-row"><strong>TOTAL: ₦{receipt_data['total']:.2f}</strong></div>
    </div>
    <div class="footer"><p>Thank you for your patronage!</p></div>
  </div>
</body>
</html>"""