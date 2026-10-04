"""
# ======================================
# ENUMERATION
# ======================================

Defines and handles the enumeration system used to fetch various types of data for the application. Mainly used 
for handling the icons, but also for loading components.
"""

from yugioh_database_global_imports_root import *
from yugioh_database_global_imports_root import enum

class SourceFetch:
    _base_path = "DATA"

    _icon_path = "icons"
    _font_path = "fonts"
    _process_model_path = "512"
    _persistent_path = "persistent"

    # =====================================
    # ICONS FETCHER
    # =====================================
    
    class IconType(enum.Enum):

        ArrowBigUp = "arrow-big-up.svg"
        ArrowBigDown = "arrow-big-down.svg"
        ArrowBigLeft = "arrow-big-left.svg"
        ArrowBigRight = "arrow-big-right.svg"
        Check = "check.svg"
        Download = "download.svg"
        CrossX = "x.svg"
        Line = "minus.svg"
        Square = "square.svg"

        LOGO_ICON = "_M[IA]sma_icon.jpg"
        CURSOR_NORMAL = "_cursor.png"
        CURSOR_PRESSED = "_cursor-hand.png"

        # yugioh
        Dark = "YG_DARK.svg"
        Divine = "YG_DIVINE.svg"
        Earth = "YG_EARTH.svg"
        Fire = "YG_FIRE.svg"
        Light = "YG_LIGHT.svg"
        Water = "YG_WATER.svg"
        Wind = "YG_Wind.svg"

        Monster = "YG_GENERIC.svg"
        Spell = "YG_SPELL.svg"
        Trap = "YG_TRAP.svg"

        SpellNormal = "YG_GENERIC.svg"
        SpellContinuous = "YG_SPELL_Continuous.svg"
        SpellEquip = "YG_SPELL_Equip.svg"
        SpellField = "YG_SPELL_Field.svg"
        SpellQuickPlay = "YG_SPELL_Quick-Play.svg"
        SpellRitual = "YG_SPELL_Ritual.svg"

        TrapNormal = "YG_GENERIC.svg"
        TrapContinuous = "YG_TRAP_Continuous.svg"
        TrapCounter = "YG_TRAP_Counter.svg"

        YugiohGeneric = "YG_GENERIC.svg"

        LMBottomCenterFULL = "YG_LM-BottomCenter_FULL.png"
        LMBottomCenterEMPTY = "YG_LM-BottomCenter_EMPTY.png"
        LMBottomLeftFULL = "YG_LM-BottomLeft_FULL.png"
        LMBottomLeftEMPTY = "YG_LM-BottomLeft_EMPTY.png"
        LMBottomRightFULL = "YG_LM-BottomRight_FULL.png"
        LMBottomRightEMPTY = "YG_LM-BottomRight_EMPTY.png"
        LMMiddleLeftFULL = "YG_LM-MiddleLeft_FULL.png"
        LMMiddleLeftEMPTY = "YG_LM-MiddleLeft_EMPTY.png"
        LMMiddleRightFULL = "YG_LM-MiddleRight_FULL.png"
        LMMiddleRightEMPTY = "YG_LM-MiddleRight_EMPTY.png"
        LMTopCenterFULL = "YG_LM-TopCenter_FULL.png"
        LMTopCenterEMPTY = "YG_LM-TopCenter_EMPTY.png"
        LMTopLeftFULL = "YG_LM-TopLeft_FULL.png"
        LMTopLeftEMPTY = "YG_LM-TopLeft_EMPTY.png"
        LMTopRightFULL = "YG_LM-TopRight_FULL.png"
        LMTopRightEMPTY = "YG_LM-TopRight_EMPTY.png"


        # when path is needed
        @property
        def path(self):
            return os.path.join(SourceFetch._base_path, SourceFetch._icon_path, self.value)
        
        # when icon is needed (setIcon() method of widgets)
        @property
        def QIcon(self):
            return QIcon(self.path)

        # when the icon has to appear next to some text (setText() method of widgets)
        def as_html(self, size=16, widget=None):
            icon = self.QIcon

            scale = 1.0
            if widget is not None:
                try:
                    screen = widget.screen()
                    if screen:
                        scale = screen.devicePixelRatio()
                except Exception:
                    pass

            actual_size = int(size * scale)
            pixmap = icon.pixmap(actual_size, actual_size)

            pixmap.setDevicePixelRatio(scale)


            ba = QByteArray()
            buffer = QBuffer(ba)
            buffer.open(QIODevice.WriteOnly)
            pixmap.save(buffer, "PNG")
            buffer.close()

            b64_data = base64.b64encode(ba.data()).decode("utf-8")

            return f'<img src="data:image/png;base64,{b64_data}" width="{size}" height="{size}">'

    # =====================================
    # FONT FETCHER
    # =====================================
    class FontPath(enum.Enum):
        
        SpaceAge = "space age.ttf"
        
        @property
        def path(self):
            return os.path.join(SourceFetch._base_path, SourceFetch._font_path, self.value)


    class EditerPath(enum.Enum):
        
        EditerProcess = "CNNetworkOBSCURE512.pth"
        EditerReverse = "CNNetworkCLAIR512.pth"
        
        @property
        def path(self):
            return os.path.join(SourceFetch._base_path, SourceFetch._process_model_path, self.value)
        
    # =====================================
    # DATA FETCHER
    # =====================================
    class PersistentDataPath(enum.Enum):
        
        AllowedChars = "Payload_alphabet.json"
        
        @property
        def path(self):
            return os.path.join(SourceFetch._base_path, SourceFetch._persistent_path, self.value)

if __name__ == "__main__":
    pass