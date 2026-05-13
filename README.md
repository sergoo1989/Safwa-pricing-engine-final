# محرك تسعير صفوة

تطبيق Streamlit لحساب تكلفة وتسعير المنتجات والبكجات اعتماداً على ملفات Zoho Inventory وZoho Books.

## المدخلات

ضع ملفات Zoho التالية داخل مجلد `data` أو ارفعها من شاشة رفع الملفات:

- `zoho_items.csv`: ملف البنود.
- `zoho_composite_items.csv`: ملف البكجات والتجميعات.
- `zoho_inventory_valuation.csv`: ملف تقييم المخزون لحساب متوسط التكلفة.

## منطق التكلفة

- يتم حساب تكلفة المواد الخام من متوسط تقييم المخزون عند توفره.
- إذا لم تتوفر قيمة من تقييم المخزون، يستخدم النظام تكلفة البند من ملف الأصناف.
- يدعم النظام البكجات التي تحتوي على بكجات أخرى مع حل التكلفة بشكل متداخل.

## التشغيل

```bash
streamlit run dashboard_pro.py --server.port 8502
```

## هيكل مهم

```text
data/
  zoho_items.csv
  zoho_composite_items.csv
  zoho_inventory_valuation.csv
pricing_app/
  zoho_loader.py
  data_loader.py
  costing.py
  advanced_pricing.py
  ui_components.py
dashboard_pro.py
```

## ملاحظات

تم حذف وحدات التحليل القديمة. إعدادات القنوات والرسوم تتم من داخل التطبيق.
