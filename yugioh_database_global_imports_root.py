import os
import sys
import json
import time
import requests
import concurrent.futures
from threading import Lock
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import gc
import re
import enum
import base64
import html
from pathlib import Path
import struct
from PIL import Image, ImageFile
from PIL.ImageQt import toqpixmap

# Handle corrupt/truncated EOF markers from source datasets
ImageFile.LOAD_TRUNCATED_IMAGES = True

from datetime import datetime
import numpy as np
import traceback

from PySide6.QtCore import (Qt, QTimer, QSize, QRect, QObject, QEvent, QRegularExpression, Signal, QThread, 
                            QByteArray, QBuffer, QIODevice, QStandardPaths, QPoint, QMutex, QMutexLocker)

from PySide6.QtGui import (
    QPixmap, QImage, QIcon, QFont, QPainter, QColor, QRegularExpressionValidator, QCursor
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QGridLayout, QLineEdit, QComboBox, QSpinBox, QLabel, QTextEdit,
    QListWidget, QListWidgetItem, QGroupBox, QPushButton, QToolButton,
    QFrame, QSizePolicy, QStackedWidget, QStackedLayout, QDialog, QToolTip, QFileDialog
)


# database source link
API_URL = "https://db.ygoprodeck.com/api/v7/cardinfo.php"


# Folder Configuration
JSON_FOLDER = "cards_data"
IMG_FULL_FOLDER = "cards_images_full"
IMG_CROP_FOLDER = "cards_images_artwork"
ICONS_FOLDER = "icons"

CARD_KINDS = ["All", "Monster", "Spell", "Trap"]
MONSTER_CATEGORIES = [
    "All", "Normal", "Effect", "Ritual", "Fusion", "Synchro", 
    "Xyz", "Link", "Pendulum"
]
SPELL_PROPERTIES = [
    "All", "Normal", "Quick-Play", "Continuous", "Equip", "Field", "Ritual"
]
TRAP_PROPERTIES = [
    "All", "Normal", "Continuous", "Counter"
]
MONSTER_ABILITIES = ["All", "Tuner", "Toon", "Gemini", "Spirit", "Union", "Flip"]
ATTRIBUTES = ["All", "FIRE", "WATER", "WIND", "EARTH", "LIGHT", "DARK", "DIVINE"]
MONSTER_TYPES = [
    "All", "Aqua", "Beast", "Beast-Warrior", "Cyberse", "Dinosaur", "Divine-Beast",
    "Dragon", "Fairy", "Fiend", "Fish", "Illusion", "Insect", "Machine", "Plant",
    "Psychic", "Pyro", "Reptile", "Rock", "Sea Serpent", "Spellcaster", "Thunder",
    "Warrior", "Winged Beast", "Wyrm", "Zombie"
]
