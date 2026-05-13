#!/bin/bash

# 🚀 سكريبت تشغيل سريع لمحرك تسعير صفوة
# Safwa Pricing Engine - Quick Start Script

echo "================================"
echo "💎 محرك تسعير صفوة"
echo "Safwa Pricing Engine v2.0"
echo "================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ خطأ: Python 3 غير مثبت"
    exit 1
fi

echo "✅ Python موجود"

# Check if in virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  تحذير: لست في بيئة افتراضية"
    echo "   يُفضل إنشاء بيئة افتراضية أولاً:"
    echo "   python3 -m venv venv && source venv/bin/activate"
    echo ""
    read -p "هل تريد المتابعة بدون بيئة افتراضية؟ (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install requirements
echo ""
echo "📦 تثبيت المتطلبات..."
pip install -q -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ فشل تثبيت المتطلبات"
    exit 1
fi

echo "✅ تم تثبيت المتطلبات بنجاح"
echo ""

# Create necessary directories
echo "📁 إنشاء المجلدات المطلوبة..."
mkdir -p data backups exports logs
echo "✅ تم إنشاء المجلدات"
echo ""

# Choose version
echo "اختر النسخة للتشغيل:"
echo "1) النسخة الأساسية (dashboard.py)"
echo "2) النسخة الاحترافية (dashboard_pro.py) ⭐ موصى بها"
echo ""
read -p "اختيارك (1/2): " version_choice

case $version_choice in
    1)
        dashboard_file="dashboard.py"
        port=8503
        echo ""
        echo "🚀 تشغيل النسخة الأساسية..."
        ;;
    2)
        dashboard_file="dashboard_pro.py"
        port=8502
        echo ""
        echo "🚀 تشغيل النسخة الاحترافية..."
        ;;
    *)
        echo "❌ اختيار غير صحيح"
        exit 1
        ;;
esac

echo ""
echo "================================"
echo "✅ جاهز للتشغيل!"
echo "📍 الرابط: http://localhost:$port"
echo "⚠️  اضغط Ctrl+C للإيقاف"
echo "================================"
echo ""

# Run Streamlit
python3 -m streamlit run $dashboard_file --server.port $port --server.headless true

echo ""
echo "👋 شكراً لاستخدام محرك تسعير صفوة"
