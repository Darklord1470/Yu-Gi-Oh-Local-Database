"""
# ======================================
# APPLICATION THEME
# ======================================

The global theme used for all the widgets of the application.
"""

from _global_enums import SourceFetch

# ======================================
# BASE COLORS
# ======================================
COLORS = {
    "bg_dark": "#16213e",        # Blu molto scuro (sfondo finestra)
    "bg_medium": "#0f3460",      # Blu meno scuro (dentro ComboBox)
    "border_medium": "#4a5f8a",  # Blu mediamente scuro (bordo ComboBox)
    "gradient_start": "#667eea", # Blu chiaro (gradient)
    "gradient_end": "#764ba2",   # Viola (gradient)
    "hover_start": "#7b93ff",    # Blu chiaro hover
    "hover_end": "#8b5bc7",      # Viola hover
    "text": "#eee",              # Testo bianco

    "deep blue": "#002fff",     # usati per la label QUICKMODE (da usare anche per il resto invece dei colori più sbiaditi?)
    "deep purple": "#c300ff",

    "cursor blue": "#3e3efd",      # usati per il cursore in entrambe le sue forme
    "cursor purple": "#fa69cd"
}


# ======================================
# PATHS FOR ICONS THAT HAVE TO BE INCLUDED HERE
# ======================================
ARROW_BIG_UP = SourceFetch.IconType.ArrowBigUp.path.replace("\\","/")
ARROW_BIG_LEFT = SourceFetch.IconType.ArrowBigLeft.path.replace("\\","/")
ARROW_BIG_DOWN = SourceFetch.IconType.ArrowBigDown.path.replace("\\","/")
CHECK = SourceFetch.IconType.Check.path.replace("\\","/")


# theme to be applied
GLOBAL_THEME = f"""
    /* Stile globale */
    QWidget {{
        background-color: #1a1a2e;
        color: #eee;
        font-family: 'Segoe UI', 'Arial', sans-serif;
        font-size: 10pt;
    }}
    
    QMainWindow {{
        background-color: #16213e;
    }}
    
    /* Pulsanti */
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #667eea, stop:1 #764ba2);
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        color: white;
        font-weight: bold;
        min-width: 80px;
    }}
    
    QPushButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);
    }}
    
    QPushButton:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #5568d3, stop:1 #633a87);
        padding-top: 12px;
        padding-bottom: 8px;
    }}
    
    /* Qui uso rgba invece della notazione esadecimale per controllare la trasparenza */
    QPushButton:disabled {{
        background: rgba(42, 42, 62, 0.6);
        color: #666;
    }}
    
    /* Input di testo */
    QLineEdit {{
        background-color: #0f3460;
        border: 2px solid #16213e;
        border-radius: 6px;
        padding: 8px 12px;
        color: #eee;
        selection-background-color: #667eea;
    }}
    
    QLineEdit:focus {{
        border: 2px solid #667eea;
        background-color: #1a4d7a;
    }}
    
    QLineEdit:hover {{
        border: 2px solid #4a5f8a;
    }}
    
    /* Area di testo */
    QTextEdit {{
        background-color: #0f3460;
        border: 2px solid #16213e;
        border-radius: 6px;
        padding: 8px;
        color: #eee;
        selection-background-color: #667eea;
    }}
    
    QTextEdit:focus {{
        border: 2px solid #667eea;
    }}

    QTextEdit:read-only {{
        background-color: #0a2340;  /* Più scuro */
        color: #aaa;                /* Testo grigio chiaro */
        border: 2px solid #1a3a5a;  /* Bordo più scuro */
    }}

    QTextEdit:disabled {{
        background-color: #0a1628;  /* Ancora più scuro */
        color: #666;                /* Testo grigio scuro */
        border: 2px solid #16213e;  /* Bordo minimo */
    }}

    /* Se vuoi che readonly + focus abbia stile diverso */
    QTextEdit:read-only:focus {{
        border: 2px solid #4a5f8a;  /* Bordo blu attenuato */
    }}
    
    /* Etichette */
    QLabel {{
        background-color: transparent;
        color: #eee;
        padding: 2px;
    }}

    QLabel:disabled {{
        background-color: transparent;
        color: #666;
        padding: 2px;
        opacity: 0.6;
    }}
    
    /* Checkbox */
    QCheckBox {{
        spacing: 8px;
        color: #eee;
    }}

    QCheckBox:unchecked {{
        color: #667eea;
    }}

    QCheckBox:checked {{
        color: #8b5bc7;
    }}
    
    QCheckBox::indicator {{
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 2px solid #4a5f8a;
        background-color: #16213e;
    }}
    
    QCheckBox::indicator:hover {{
        border: 2px solid #667eea;
        background-color: #0f3460;
    }}

    QCheckBox::indicator:unchecked {{
        background-color: #16213e;
        border: 2px solid #4a5f8a;
    }}

    QCheckBox::indicator:unchecked:hover {{
        background-color: #0f3460;
        border: 2px solid #667eea;
        color: #667eea;
    }}
        
    QCheckBox::indicator:checked {{
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #667eea, stop:1 #764ba2);  /* ⭐ Gradient tema */
        border: 2px solid #667eea;
        /* Spunta bianca */
        image: url({CHECK});
    }}

    QCheckBox::indicator:checked:hover {{
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);  /* ⭐ Gradient più chiaro (hover) */
        border: 2px solid #7b93ff;
    }}

    /* Slider */
    QSlider::groove:horizontal {{
        border: none;
        height: 6px;
        background: #0f3460;
        border-radius: 3px;
    }}
    
    QSlider::handle:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #667eea, stop:1 #764ba2);
        border: none;
        width: 18px;
        height: 18px;
        margin: -6px 0;
        border-radius: 9px;
    }}
    
    QSlider::handle:horizontal:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);
    }}
    
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #667eea, stop:1 #764ba2);
        border-radius: 3px;
    }}

    /* --- Stato DISABILITATO --- */
    QSlider:disabled {{
        opacity: 0.6; /* attenua tutto lo slider */
    }}

    QSlider::groove:horizontal:disabled {{
        background: #1e1e2f;
    }}

    QSlider::handle:horizontal:disabled {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #4a4a6a, stop:1 #5a5a7a);
    }}

    QSlider::sub-page:horizontal:disabled {{
        background: #3a3a55;
    }}

    
    /* Progress Bar */
    QProgressBar {{
        border: none;
        border-radius: 8px;
        background-color: #0f3460;
        text-align: center;
        color: white;
        font-weight: bold;
        height: 20px;
    }}
    
    QProgressBar::chunk {{
        border-radius: 8px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #667eea, stop:1 #764ba2);
    }}
    
    /* Scrollbar */
    QScrollBar:vertical {{
        background: #16213e;
        width: 14px;
        border-radius: 7px;
        margin: 0px;
    }}
    
    QScrollBar::handle:vertical {{
        background: #667eea;
        border-radius: 7px;
        min-height: 30px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background: #7b93ff;
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    /* ComboBox */
    QComboBox {{
        background-color: #0f3460;
        border: 2px solid #16213e;
        border-radius: 6px;
        padding: 8px 12px;
        color: #eee;
        min-width: 150px;
    }}

    QComboBox:hover {{
        border: 2px solid #4a5f8a;
        background-color: #1a4d7a;
    }}

    QComboBox:focus {{
        border: 2px solid #667eea;
        background-color: #1a4d7a;
    }}

    QComboBox:disabled {{
        background-color: #0a2340;
        color: #666;
        border: 2px solid #0a2340;
    }}

    /* Freccia dropdown */
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 30px;
        border-left: 1px solid #16213e;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #667eea, stop:1 #764ba2);
    }}

    QComboBox::drop-down:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);
    }}

    QComboBox::drop-down:disabled {{
        background: #2a2a3e;
    }}

    QComboBox::down-arrow {{
        image: url({ARROW_BIG_LEFT});
        width: 14px;
        height: 14px;
    }}

    /* quando il menu è aperto */
    QComboBox::down-arrow:on {{
        image: url({ARROW_BIG_DOWN});
    }}

    QComboBox::down-arrow:disabled {{
        background: #2a2a3e;
    }}

    /* Menu dropdown */
    QComboBox QAbstractItemView {{
        background-color: #0f3460;
        border: 2px solid #667eea;
        border-radius: 6px;
        selection-background-color: #667eea;
        selection-color: white;
        color: #eee;
        padding: 4px;
        outline: none;
    }}

    QComboBox QAbstractItemView::item {{
        padding: 8px 12px;
        border-radius: 4px;
        margin: 2px;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background-color: #1a4d7a;
    }}

    QComboBox QAbstractItemView::item:selected {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #667eea, stop:1 #764ba2);
        color: white;
    }}



    /* ============================================
    CUSTOM TITLE BAR - Override regole generali
    ============================================ */

    /* Title bar container */
    #customTitleBar {{
        background-color: #16213e;
        border-bottom: 1px solid #667eea;
    }}

    /* Label del titolo */
    #titleBarLabel {{
        color: white;
        font-weight: bold;
        font-size: 12pt;
        padding: 0px;
        background: transparent;
    }}

    /* Pulsanti title bar - OVERRIDE dello stile globale QPushButton */
    #titleBarButton, #titleBarCloseButton {{
        background: transparent;
        border: none;
        border-radius: 0px;  /* No border radius */
        color: white;
        font-size: 16px;
        padding: 5px 15px;
        min-width: 0px;  /* ⭐ IMPORTANTE: Rimuovi min-width */
        max-width: 45px;  /* ⭐ Limita larghezza massima */
        font-weight: normal;  /* Non bold */
    }}

    #titleBarButton:hover {{
        background: rgba(255, 255, 255, 0.2);
    }}

    #titleBarButton:pressed {{
        background: rgba(255, 255, 255, 0.3);
        padding-top: 5px;  /* No shift */
        padding-bottom: 5px;
    }}

    /* Pulsante chiudi con hover rosso */
    #titleBarCloseButton:hover {{
        background: #e74c3c;
    }}

    #titleBarCloseButton:pressed {{
        background: #c0392b;
    }}






    /* ============================================
    CHECKBOX QUICK MODE
    ============================================ */

    /* Testo della checkbox con gradient */
    QCheckBox#quickModeCheckbox {{
        font-weight: bold;
        font-size: 11pt;
        padding: 8px;
    }}

    QCheckBox#quickModeCheckbox:unchecked {{
        color: #667eea;
    }}

    QCheckBox#quickModeCheckbox::indicator {{
        width: 28px;
        height: 28px;
        border-radius: 6px;
        border: 3px solid #4a5f8a;  /* ⭐ Blu mediamente scuro (bordo ComboBox) */
        background-color: #16213e;   /* ⭐ Blu molto scuro (sfondo finestra) */
    }}

    /* Hover - Non selezionato */
    QCheckBox#quickModeCheckbox::indicator:hover {{
        border: 3px solid #667eea;   /* ⭐ Blu chiaro (gradient start) */
        background-color: #0f3460;   /* ⭐ Blu meno scuro (dentro ComboBox) */
    }}

    /* Non selezionato (stato normale) */
    QCheckBox#quickModeCheckbox::indicator:unchecked {{
        background-color: #16213e;   /* ⭐ Blu molto scuro */
        border: 3px solid #4a5f8a;   /* ⭐ Blu mediamente scuro */
    }}

    QCheckBox#quickModeCheckbox::indicator:unchecked:hover {{
        background-color: #0f3460;   /* ⭐ Blu meno scuro */
        border: 3px solid #667eea;   /* ⭐ Blu chiaro */
        color: #667eea;
    }}

    /* ⭐ Selezionato - Gradient Blu→Viola */
    QCheckBox#quickModeCheckbox::indicator:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #667eea, stop:1 #764ba2);  /* ⭐ Gradient tema */
        border: 3px solid #667eea;
        image: url({CHECK});
    }}

    QCheckBox#quickModeCheckbox:checked {{
        color: #8b5bc7;
    }}

    /* Hover - Selezionato */
    QCheckBox#quickModeCheckbox::indicator:checked:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);  /* ⭐ Gradient più chiaro (hover) */
        border: 3px solid #7b93ff;
    }}

    /* Testo quando disabilitata */
    QCheckBox#quickModeCheckbox:disabled {{
        color: #4a5f8a;  /* ⭐ Grigio-blu scuro (opaco) */
    }}

    /* Indicatore disabilitato - Non selezionato */
    QCheckBox#quickModeCheckbox::indicator:disabled {{
        background-color: #0a2340;   /* ⭐ Blu molto scuro (quasi nero) */
        border: 3px solid #2a3a5a;   /* ⭐ Bordo grigio-blu scuro */
    }}

    /* Indicatore disabilitato - Selezionato */
    QCheckBox#quickModeCheckbox::indicator:checked:disabled {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #4a5f8a, stop:1 #5a4a7a);  /* ⭐ Gradient desaturato */
        border: 3px solid #4a5f8a;
        /* Mantieni checkmark ma con opacità ridotta */
        image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><path d='M13.33 4L6 11.33 2.66 8' fill='none' stroke='%23666' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>");
    }}

    /* Nessun hover quando disabilitato */
    QCheckBox#quickModeCheckbox::indicator:disabled:hover {{
        background-color: #0a2340;   /* ⭐ Nessun cambio su hover */
        border: 3px solid #2a3a5a;
    }}

    QCheckBox#quickModeCheckbox::indicator:checked:disabled:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                    stop:0 #4a5f8a, stop:1 #5a4a7a);
        border: 3px solid #4a5f8a;
    }}











    /* ============================================
    TOOLTIP
    ============================================ */

    QToolTip {{
        background-color: #0f3460;  /* Blu meno scuro */
        color: #eee;
        border: 2px solid #667eea;  /* Blu chiaro */
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 10pt;
        font-family: 'Segoe UI', 'Arial', sans-serif;

        
        /* ⭐ QUESTE SONO LE RIGHE CHIAVE ⭐ */
        max-width: 800px;        /* Larghezza massima */
        white-space: normal;      /* Permetti word wrap */
    }}

    
    /* ============================================
    SPINBOX (QSpinBox e QDoubleSpinBox)
    ============================================ */

    QSpinBox, QDoubleSpinBox {{
        background-color: #0f3460;
        border: 2px solid #16213e;
        border-radius: 6px;
        padding: 8px 12px;
        color: #eee;
        selection-background-color: #667eea;
        min-height: 28px;
    }}

    QSpinBox:hover, QDoubleSpinBox:hover {{
        border: 2px solid #4a5f8a;
        background-color: #1a4d7a;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 2px solid #667eea;
        background-color: #1a4d7a;
    }}

    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background-color: #0a2340;
        color: #666;
        border: 2px solid #0a2340;
    }}

    /* Frecce su/giù */
    QSpinBox::up-button, QDoubleSpinBox::up-button {{
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        border-left: 1px solid #16213e;
        border-top-right-radius: 6px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #667eea, stop:1 #764ba2);
    }}

    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);
    }}

    QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #5568d3, stop:1 #633a87);
    }}

    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        border-left: 1px solid #16213e;
        border-bottom-right-radius: 6px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #667eea, stop:1 #764ba2);
    }}

    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);
    }}

    QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #5568d3, stop:1 #633a87);
    }}

    /* Icone frecce (Unicode arrows) */
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: url({ARROW_BIG_UP});
        width: 12px;
        height: 12px;
    }}
    
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: url({ARROW_BIG_DOWN});
        width: 12px;
        height: 12px;
    }}

    /* Quando disabilitato */
    QSpinBox::up-button:disabled, QDoubleSpinBox::up-button:disabled,
    QSpinBox::down-button:disabled, QDoubleSpinBox::down-button:disabled {{
        background: #2a2a3e;
    }}



    /* ============================================
    TAB WIDGET
    ============================================ */

    QTabWidget {{
        background-color: #1a1a2e;
        border: none;
    }}

    QTabWidget::pane {{
        border: 2px solid #667eea;
        border-radius: 8px;
        background-color: #1a1a2e;
        top: -2px;
        padding: 10px;
    }}

    QTabBar {{
        background-color: transparent;
        qproperty-drawBase: 0;
    }}

    QTabBar::tab {{
        background-color: #16213e;
        color: #aaa;
        border: 2px solid #4a5f8a;
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 12px 24px;
        margin-right: 4px;
        font-weight: bold;
        font-size: 11pt;
        min-width: 100px;
    }}

    QTabBar::tab:hover {{
        background-color: #0f3460;
        color: #eee;
        border-color: #667eea;
    }}

    QTabBar::tab:selected {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #667eea, stop:1 #764ba2);
        color: white;
        border-color: #667eea;
        border-bottom: 2px solid #667eea;
    }}

    QTabBar::tab:selected:hover {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);
    }}

    QTabBar::tab:disabled {{
        background-color: #0a1628;
        color: #555;
        border-color: #2a2a3e;
    }}

    QTabBar::tab:first {{
        margin-left: 0px;
    }}

    QTabBar::tab:last {{
        margin-right: 0px;
    }}

    QTabBar::scroller {{
        width: 40px;
    }}

    QTabBar QToolButton {{
        background-color: #16213e;
        border: 2px solid #4a5f8a;
        border-radius: 4px;
        color: #eee;
        padding: 4px;
    }}

    QTabBar QToolButton:hover {{
        background-color: #0f3460;
        border-color: #667eea;
    }}

    QTabBar QToolButton::right-arrow {{
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQgMkw4IDZMNCAxMCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+Cg==);
    }}

    QTabBar QToolButton::left-arrow {{
        image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTggMkw0IDZMOCA0IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
    }}




    /* ============================================
    SIDEBAR + STACKED WIDGET
    ============================================ */

    /* Sidebar container */
    #sidebar {{
        background-color: #16213e;
        border-right: 2px solid #667eea;
    }}

    /* Titolo sidebar */
    #sidebarTitle {{
        color: #667eea;
        font-size: 14pt;
        font-weight: bold;
        padding: 10px;
    }}

    /* Bottoni di navigazione */
    QPushButton#navButton {{
        background-color: transparent;
        color: #aaa;
        border: none;
        border-left: 4px solid transparent;
        border-radius: 0px;
        padding: 14px 20px;
        text-align: left;
        font-size: 11pt;
        font-weight: bold;
    }}

    /* Bottone hover */
    QPushButton#navButton:hover {{
        background-color: #0f3460;
        color: #eee;
        border-left: 4px solid #667eea;
    }}

    /* Bottone selezionato (checked) */
    QPushButton#navButton:checked {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #667eea, stop:1 #764ba2);
        color: white;
        border-left: 4px solid #667eea;
    }}

    /* Bottone selezionato + hover */
    QPushButton#navButton:checked:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #7b93ff, stop:1 #8b5bc7);
    }}

    /* Bottone disabilitato */
    QPushButton#navButton:disabled {{
        background-color: transparent;
        color: #555;
        border-left: 4px solid transparent;
    }}

    /* Content Stack */
    #contentStack {{
        background-color: #1a1a2e;
        border: none;
    }}

    /* Ogni widget dentro lo stack */
    #contentStack > QWidget {{
        background-color: #1a1a2e;
    }}





    /* ============================================
    RIGHT PANEL (Buffer)
    ============================================ */

    /* Pannello destro container */
    #rightPanel {{
        background-color: #16213e;
        border-left: 2px solid #667eea;
    }}

    /* Header del pannello */
    #panelHeader {{
        background-color: #0f3460;
        border-bottom: 2px solid #4a5f8a;
    }}

    /* Titolo pannello */
    #panelTitle {{
        color: #764ba2;
        font-size: 20pt;
        font-weight: bold;
    }}

    /* Sottotitolo pannello */
    #panelSubtitle {{
        color: #aaa;
        font-size: 9pt;
    }}

    /* Buffer Stack */
    #bufferStack {{
        background-color: #16213e;
    }}

    /* Quick Mode Label nella sidebar */
    #quickModeLabel {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                    stop:0 #002fff, stop:1 #c300ff);    /*BELLISSIMA COMBINAZIONE!!!!*/
        color: white;
        padding: 8px;
        border-radius: 6px;
        font-size: 14pt;
        font-weight: bold;
    }}



    /* Drag & Drop Area */
    #dragDropArea[InteractionState="normal"] {{
        background-color: #0f3460;
        border: 3px dashed #4a5f8a;
        border-radius: 12px;
    }}

    #dragDropArea[InteractionState="hover"] {{
        background-color: #1a4d7a;
        border: 3px dashed #667eea;
        border-radius: 12px;
    }}

    #dragDropArea[InteractionState="drag"] {{
        background-color: #1a4d7a;
        border: 3px solid #667eea;
        border-radius: 12px;
    }}

    #dragDropArea * {{
        background: transparent;
    }} 

    #dragDropArea:disabled {{
        background-color: #0a1628;
        color: #666;
        border: 3px solid #16213e;
        border-radius: 12px;
    }}

"""