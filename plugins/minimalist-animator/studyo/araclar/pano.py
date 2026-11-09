"""Tüm projelerin tek bakışta durumu (Yönetici her oturumun başında çalıştırır): ma pano"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from proje import pano  # noqa: E402

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    pano()
