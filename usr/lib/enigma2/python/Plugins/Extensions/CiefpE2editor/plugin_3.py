import os
import shutil
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.Screen import Screen

# Plugin identity parameters
PLUGIN_NAME = "CiefpWhitelistStreamrelay"
PLUGIN_DESC = "Creates a whitelist_streamrelay file from userbouquet data"
PLUGIN_VERSION = "1.4"

# Configuration file paths
WHITE_LIST_FILE = 'whitelist_streamrelay'
WHITE_LIST_PATH = '/etc/enigma2/whitelist_streamrelay'
USER_BOUQUET_DIR = '/etc/enigma2/'
PLUGIN_ICON = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/icon.png"

# Target userbouquet configuration array
USER_BOUQUETS = [
    'userbouquet.ciefp_19e_skydesport.tv',
    'userbouquet.ciefp_19e_skydemovies.tv',
    'userbouquet.ciefp_19e_skydedocu.tv',
    'userbouquet.ciefp_28e_skyuksports.tv',
    'userbouquet.ciefp_28e_skyukmovie.tv',
    'userbouquet.ciefp_28e_skyukdocuments.tv',
    'userbouquet.ciefp_28e_skyukkids.tv',
]

# Exclusion reference list
IGNORE_REFERENCES = [
    '1:0:19:1332:3EF:1:C00000:0:0:0:',
    '1:0:19:132F:3EF:1:C00000:0:0:0:',
    '1:0:19:1330:3EF:1:C00000:0:0:0:',
    '1:0:19:152D:455:1:C00000:0:0:0:',
    '1:0:19:283D:3FB:1:C00000:0:0:0:',
    '1:0:19:2B66:3F3:1:C00000:0:0:0:',
    '1:0:19:33AC:3EB:1:C00000:0:0:0:',
    '1:0:19:7D:B:85:C00000:0:0:0:',
    '1:0:19:6FEE:436:1:C00000:0:0:0:',
    '1:0:19:6FEF:436:1:C00000:0:0:0:',
]

def process_bouquet_line(line):
    """Processes lines by stripping service flags and verifying exclusion filters"""
    if line.startswith('#SERVICE 1:0:19:'):
        service_ref = line.replace('#SERVICE ', '').strip()
        if service_ref not in IGNORE_REFERENCES:
            return service_ref
    return None

def filter_valid_lines(file_path):
    """Parses bouquet files to harvest appropriate stream references"""
    valid_lines = []
    with open(file_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith(('#NAME', '#SERVICE 1:64', '#DESCRIPTION')):
                continue
            processed_line = process_bouquet_line(line)
            if processed_line:
                valid_lines.append(processed_line)
    return valid_lines

def process_bouquets():
    """Aggregates matching records across all designated source lists"""
    final_lines = []
    for bouquet in USER_BOUQUETS:
        bouquet_path = os.path.join(USER_BOUQUET_DIR, bouquet)
        if os.path.exists(bouquet_path):
            valid_lines = filter_valid_lines(bouquet_path)
            final_lines.extend(valid_lines)
    return final_lines

def create_whitelist_file():
    """Commits filtered channel map markers into system storage location"""
    processed_lines = process_bouquets()
    if processed_lines:
        with open(WHITE_LIST_PATH, 'w') as f:
            for line in processed_lines:
                f.write(f"{line}\n")
    return len(processed_lines)

class WhitelistScreen(Screen):
    """Full HD Execution Interface for compiling hardware Streamrelay whitelists"""

    skin = """
    <screen name="WhitelistScreen" position="center,center" size="1920,1080" title="..:: Ciefp Whitelist Streamrelay ::.." backgroundColor="#011a2e">
        <!-- Header Panel Title -->
        <widget name="plugin_title" position="0,10" size="1920,45" font="Bold;32" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" zPosition="1" />
        
        <!-- Left Side Information Box Description -->
        <widget name="description_box" position="60,90" size="1000,800" font="Regular;28" foregroundColor="#FFFFFF" backgroundColor="#011a2e" transparent="1" valign="top" zPosition="1" />
        
        <!-- Right Side Preview Image Frame Component -->
        <widget name="logo_whitelist" position="1100,90" size="800,800" zPosition="1" />
        
        <!-- Bottom Process Output Line Status -->
        <widget name="status" position="60,920" size="1200,50" font="Regular;26" halign="left" valign="center" foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1" zPosition="1" />
        
        <!-- Functional Buttons Navigation Layout -->
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/red.png" position="60,1000" size="40,40" alphatest="blend" zPosition="1" />
        <widget name="key_red" position="110,1000" size="250,40" font="Bold;28" halign="left" valign="center" transparent="1" foregroundColor="#FFFFFF" zPosition="1" />
        
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/green.png" position="360,1000" size="40,40" alphatest="blend" zPosition="1" />
        <widget name="key_green" position="410,1000" size="250,40" font="Bold;28" halign="left" valign="center" transparent="1" foregroundColor="#FFFFFF" zPosition="1" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        
        self["plugin_title"] = Label("..:: Ciefp Whitelist Streamrelay ::.. (v1.4)")
        self["status"] = Label("Initializing background modules...")
        self["logo_whitelist"] = Pixmap()
        
        self["key_red"] = Label("Close")
        self["key_green"] = Label("Process Data")

        # Static informational instructions block layout
        info_text = (
            "CiefpWhitelistStreamrelay\n\n"
            "CiefpWhitelistStreamrelay is a specialized utility module for Enigma2 receivers. \n"
            "designed for automated generation of`whitelist_streamrelay` file  \n"
            "using data from predefined userbouquet files: \n"
            " 'userbouquet.ciefp_19e_skydesport.tv', \n"
            " 'userbouquet.ciefp_19e_skydemovies.tv', \n"
            " 'userbouquet.ciefp_19e_skydedocu.tv', \n"
            " 'userbouquet.ciefp_28e_skyuksports.tv', \n"
            " 'userbouquet.ciefp_28e_skyukmovie.tv', \n"
            " 'userbouquet.ciefp_28e_skyukdocuments.tv', \n"
            " 'userbouquet.ciefp_28e_skyukkids.tv',\n\n"
            "Key Parameters:\n"
            " - Target: /etc/enigma2/whitelist_streamrelay\n"
            " - Scope: Parses system userbouquets dynamically.\n"
            " - Condition: Strips blacklisted stream paths automatically.\n\n"
            "This plugin was specifically created for ciefpsettings, \n"
            "it will not work with other settings.\n\n"
            "..:: CiefpSettings ::.."
        )
        self["description_box"] = Label(info_text)

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions"], 
            {
                "cancel": self.close, 
                "red": self.close,
                "ok": self.restart_enigma,
                "green": self.run_plugin
            }, 
            -1
        )
        self.onLayoutFinish.append(self.set_logo)

    def set_logo(self):
        logo_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/logo_whitelist.png"
        if os.path.exists(logo_path):
            self["logo_whitelist"].instance.setPixmapFromFile(logo_path)
        else:
            self["status"].setText("Graphical asset 'logo.png' could not be resolved.")
            
    def run_plugin(self):
        try:
            if os.path.exists(WHITE_LIST_PATH):
                self["status"].setText("Purging obsolete configuration entries...")
                os.remove(WHITE_LIST_PATH)

            self["status"].setText("Compiling whitelist files from target source structures...")
            lines_created = create_whitelist_file()

            self["status"].setText(f"File created with {lines_created} stream nodes. Press OK to reboot GUI.")
            self.session.open(MessageBox, f"Success!\n\nWhitelist generated with {lines_created} entries.\nPress OK to restart Enigma2 interface.", MessageBox.TYPE_INFO)
        except Exception as e:
            self["status"].setText(f"Execution Error: {str(e)}")

    def restart_enigma(self):
        """Triggers system restart configuration checks following confirmation flags"""
        self.session.openWithCallback(self.confirm_restart, MessageBox, "Do you want to restart Enigma2 now to apply the new whitelist settings?", MessageBox.TYPE_YESNO)

    def confirm_restart(self, confirmed):
        if confirmed:
            self.close()
            os.system("killall -9 enigma2")

def run_plugin(session, **kwargs):
    session.open(WhitelistScreen)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name=f"{PLUGIN_NAME} v{PLUGIN_VERSION}",
            description=PLUGIN_DESC,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon=PLUGIN_ICON,
            fnc=run_plugin,
        )
    ]