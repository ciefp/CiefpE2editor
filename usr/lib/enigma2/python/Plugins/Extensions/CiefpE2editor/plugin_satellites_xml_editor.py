from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.List import List
from Components.config import ConfigInteger, ConfigSelection, getConfigListEntry
from enigma import eTimer, eServiceCenter, eServiceReference, iServiceInformation
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
import os
from datetime import datetime

PLUGIN_VERSION = "1.2"
PLUGIN_ICON = "icon.png"
PLUGIN_NAME = "CiefpSatellitesXmlEditor"
PLUGIN_DESCRIPTION = "Edit satellites.xml file"
SATELLITES_XML_PATH = "/etc/tuxbox/satellites.xml"
SATELLITES_XML_PATH_ENIGMA2 = "/etc/enigma2/satellites.xml"

POLARIZATION = {"0": "Horizontal", "1": "Vertical", "2": "Left", "3": "Right"}
FEC_INNER = {"0": "Auto", "1": "1/2", "2": "2/3", "3": "3/4", "4": "5/6", "5": "7/8", "6": "8/9", "7": "3/5", "8": "4/5", "9": "9/10"}
SYSTEM = {"0": "DVB-S", "1": "DVB-S2", "2": "None"}
MODULATION = {"0": "Auto", "1": "QPSK", "2": "8PSK", "3": "QAM16", "4": "16APSK", "5": "32APSK", "6": "None"}
PLS_MODE = {"0": "Root", "1": "Gold", "2": "Auto", "3": "Unknown"}

class CiefpSatelliteXmlReader(Screen):
    """Full HD Screen for browsing and managing satellites.xml configuration"""
    
    skin = """
    <screen name="CiefpSatelliteXmlReader" position="center,center" size="1920,1080" title="..:: Ciefp Satellites.xml Reader ::.." backgroundColor="#011a2e">
        <!-- Right side image panel component -->
        <widget name="background" position="1400,90" size="500,800" zPosition="1" />
        
        <!-- Header Title -->
        <widget name="plugin_title" position="0,10" size="1920,45" font="Bold;32" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" zPosition="1" />
        
        <!-- Main Content List -->
        <widget source="list" render="Listbox" position="60,90" size="1300,800" scrollbarMode="showOnDemand" itemHeight="40" font="Regular;28" backgroundColor="#011a2e" zPosition="1">
            <convert type="StringList" />
        </widget>
        
        <!-- Status Information Line -->
        <widget name="status" position="60,920" size="1300,50" font="Regular;26" halign="left" valign="center" foregroundColor="#00FF00" backgroundColor="#011a2e" transparent="1" zPosition="1" />
        
        <!-- Color Buttons Layout -->
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/red.png" position="60,1000" size="40,40" alphatest="blend" zPosition="1" />
        <widget name="key_red" position="110,1000" size="200,40" font="Bold;28" halign="left" valign="center" transparent="1" foregroundColor="#FFFFFF" zPosition="1" />
        
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/green.png" position="360,1000" size="40,40" alphatest="blend" zPosition="1" />
        <widget name="key_green" position="410,1000" size="200,40" font="Bold;28" halign="left" valign="center" transparent="1" foregroundColor="#FFFFFF" zPosition="1" />
        
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/yellow.png" position="660,1000" size="40,40" alphatest="blend" zPosition="1" />
        <widget name="key_yellow" position="710,1000" size="200,40" font="Bold;28" halign="left" valign="center" transparent="1" foregroundColor="#FFFFFF" zPosition="1" />
        
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/blue.png" position="960,1000" size="40,40" alphatest="blend" zPosition="1" />
        <widget name="key_blue" position="1010,1000" size="300,40" font="Bold;28" halign="left" valign="center" transparent="1" foregroundColor="#FFFFFF" zPosition="1" />
    </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.list = []
        self["list"] = List(self.list)
        
        self["plugin_title"] = Label("..:: Ciefp Satellites.xml Reader ::..")
        self["status"] = Label("Loading XML configuration file...")
        self["background"] = Pixmap()
        
        self["key_red"] = Label("Delete")
        self["key_green"] = Label("Save Changes")
        self["key_yellow"] = Label("Edit Line")
        self["key_blue"] = Label("Add Transponder")
        
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.okPressed,
            "cancel": self.close,
            "red": self.deleteLine,
            "green": self.saveChanges,
            "yellow": self.editLine,
            "blue": self.addLine
        }, -1)
        
        self.tree = None
        self.focusTimer = eTimer()
        self.focusTimer.callback.append(self.setFocusToCurrent)
        self.onLayoutFinish.append(self.init_screen_assets)

    def init_screen_assets(self):
        img_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/satellitesxml.png"
        if os.path.exists(img_path):
            self["background"].instance.setPixmapFromFile(img_path)
        self.loadXml()

    def loadXml(self):
        try:
            self.tree = ET.parse(SATELLITES_XML_PATH)
            self.updateList()
            self.focusTimer.start(100, True)
            self["status"].setText("Configuration loaded. Press Yellow to Edit, Blue to Add, Red to Delete.")
        except Exception as e:
            print(f"[CiefpSatelliteXmlReader] Error loading satellites.xml: {str(e)}")
            self["status"].setText("Failed to read satellites.xml config!")
            self.session.open(MessageBox, f"Error loading satellites.xml: {str(e)}", MessageBox.TYPE_ERROR)

    def convertOrbitalPos(self, pos):
        pos = int(pos)
        if pos > 1800:
            return pos - 3600
        else:
            return pos

    def getCurrentTransponderData(self):
        service = self.session.nav.getCurrentService()
        if not service:
            print("[CiefpSatelliteXmlReader] No active service found")
            return None
        frontendInfo = service.frontendInfo()
        if not frontendInfo:
            print("[CiefpSatelliteXmlReader] No frontend info available")
            return None
        frontendData = frontendInfo.getAll(True)
        if not frontendData or frontendData.get("tuner_type", "") != "DVB-S":
            print(f"[CiefpSatelliteXmlReader] Invalid tuner type: {frontendData.get('tuner_type', 'Unknown')}")
            return None
        
        data = {
            "orbital_position": self.convertOrbitalPos(frontendData.get("orbital_position", 0)),
            "frequency": frontendData.get("frequency", 0) // 1000,
            "symbol_rate": frontendData.get("symbol_rate", 0) // 1000,
            "polarization": int(frontendData.get("polarization", 0)),
            "fec_inner": int(frontendData.get("fec_inner", 0)),
            "system": int(frontendData.get("system", 0)),
            "modulation": int(frontendData.get("modulation", 0)),
        }
        print(f"[CiefpSatelliteXmlReader] Current transponder data: {data}")
        return data

    def setFocusToCurrent(self):
        current_data = self.getCurrentTransponderData()
        if not current_data:
            print("[CiefpSatelliteXmlReader] No current transponder data, keeping focus on first row")
            return
        
        found_index = -1
        current_sat = None
        for idx, (text, elem) in enumerate(self.list):
            if elem.tag == "sat":
                sat_pos = int(elem.get("position", "0"))
                if sat_pos == current_data["orbital_position"]:
                    current_sat = elem
                    found_index = idx
            elif elem.tag == "transponder" and current_sat:
                trans_freq = int(elem.get("frequency", "0")) // 1000
                trans_sr = int(elem.get("symbol_rate", "0")) // 1000
                trans_pol = int(elem.get("polarization", "0"))
                trans_fec = int(elem.get("fec_inner", "0"))
                trans_sys = int(elem.get("system", "0"))
                trans_mod = int(elem.get("modulation", "0"))
                
                if (trans_freq == current_data["frequency"] and
                    trans_sr == current_data["symbol_rate"] and
                    trans_pol == current_data["polarization"] and
                    trans_fec == current_data["fec_inner"] and
                    trans_sys == current_data["system"] and
                    trans_mod == current_data["modulation"]):
                    found_index = idx
                    break
        
        if found_index != -1 and found_index < len(self.list):
            self["list"].setIndex(found_index)

    def updateList(self):
        self.list = []
        root = self.tree.getroot()
        for sat in root.findall("sat"):
            sat_name = sat.get("name")
            sat_pos = sat.get("position")
            self.list.append((f"Satellite: {sat_name} ({sat_pos})", sat))
            for trans in sat.findall("transponder"):
                freq = int(trans.get("frequency", "0")) // 1000
                sr = int(trans.get("symbol_rate", "0")) // 1000
                pol = POLARIZATION.get(trans.get("polarization", "0"), "Unknown")
                fec = FEC_INNER.get(trans.get("fec_inner", "0"), "Unknown")
                sys = SYSTEM.get(trans.get("system", "0"), "Unknown")
                mod = MODULATION.get(trans.get("modulation", "0"), "Unknown")
                
                extra = []
                is_id = trans.get("is_id")
                pls_mode = trans.get("pls_mode")
                pls_code = trans.get("pls_code")
                t2mi_plp_id = trans.get("t2mi_plp_id")
                t2mi_pid = trans.get("t2mi_pid")
                
                if is_id and int(is_id) > 0:
                    extra.append(f"MIS: is_id={is_id}, pls_mode={PLS_MODE.get(pls_mode, 'Unknown')}, pls_code={pls_code}")
                if t2mi_plp_id and int(t2mi_plp_id) >= 0:
                    extra.append(f"T2-MI: plp_id={t2mi_plp_id}, pid={t2mi_pid or '0'}")
                
                display_text = f"  TR: {freq} {pol} {sr} {fec} {sys} {mod}"
                if extra:
                    display_text += f" [{' | '.join(extra)}]"
                
                self.list.append((display_text, trans))
        self["list"].setList(self.list)

    def okPressed(self):
        self.editLine()

    def deleteLine(self):
        cur = self["list"].getCurrent()
        if cur and isinstance(cur[1], ET.Element):
            root = self.tree.getroot()
            if cur[1].tag == "sat":
                root.remove(cur[1])
                self["status"].setText("Selected Satellite entry removed.")
            elif cur[1].tag == "transponder":
                for sat in root.findall("sat"):
                    for trans in sat.findall("transponder"):
                        if trans == cur[1]:
                            sat.remove(trans)
                            break
                    else:
                        continue
                    break
                self["status"].setText("Selected Transponder entry removed.")
            self.updateList()

    def saveChanges(self):
        try:
            self["status"].setText("Saving satellites.xml file locations...")
            rough_string = ET.tostring(self.tree.getroot(), encoding='iso-8859-1')
            parsed = minidom.parseString(rough_string)
            pretty_xml = parsed.toprettyxml(indent="\t", encoding='iso-8859-1').decode('iso-8859-1')
            
            lines = pretty_xml.split('\n')
            filtered_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('<?xml') and not stripped.startswith('<!'):
                    filtered_lines.append(line.rstrip())
                elif stripped.startswith('<?xml') or stripped.startswith('<!'):
                    filtered_lines.append(line)
            
            current_date = datetime.now().strftime("%d.%m.%Y")
            header = f"""<?xml version="1.0" encoding="iso-8859-1"?>
<!--
\tFile edited by ciefp satellite.xml editor, {current_date}
-->
"""
            final_xml = header + '\n'.join(filtered_lines[1:])
            
            with open(SATELLITES_XML_PATH, 'w', encoding='iso-8859-1') as f:
                f.write(final_xml)
            
            try:
                with open(SATELLITES_XML_PATH_ENIGMA2, 'w', encoding='iso-8859-1') as f:
                    f.write(final_xml)
            except Exception as e:
                print(f"[CiefpSatelliteXmlReader] Error saving to {SATELLITES_XML_PATH_ENIGMA2}: {str(e)}")
            
            self["status"].setText("Changes committed successfully to system directories!")
            self.session.open(MessageBox, "Changes saved successfully to both system paths!", MessageBox.TYPE_INFO)
        except Exception as e:
            print(f"[CiefpSatelliteXmlReader] Error saving satellites.xml: {str(e)}")
            self["status"].setText("Error encountered while performing file write operations.")
            self.session.open(MessageBox, f"Error saving satellites.xml: {str(e)}", MessageBox.TYPE_ERROR)

    def editLine(self):
        cur = self["list"].getCurrent()
        if cur and isinstance(cur[1], ET.Element) and cur[1].tag == "transponder":
            self.session.openWithCallback(self.updateList, CiefpSatelliteXmlEditor, cur[1], False)

    def addLine(self):
        cur = self["list"].getCurrent()
        if cur and isinstance(cur[1], ET.Element) and cur[1].tag == "sat":
            self.session.openWithCallback(self.updateList, CiefpSatelliteXmlEditor, cur[1], True)

class CiefpSatelliteXmlEditor(ConfigListScreen, Screen):
    """Full HD Screen for processing configuration properties of standard/multistream transponders"""
    
    skin = """
    <screen name="CiefpSatelliteXmlEditor" position="center,center" size="1920,1080" title="..:: Ciefp Satellites.xml Parameters Editor ::.." backgroundColor="#011a2e">
        <!-- Right side preview image panel component -->
        <widget name="background" position="1300,90" size="600,800" zPosition="1" />
        
        <!-- Header Title -->
        <widget name="plugin_title" position="0,10" size="1920,45" font="Bold;32" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" zPosition="1" />
        
        <!-- Configuration Properties Selection Block -->
        <widget name="config" position="60,90" size="1200,800" scrollbarMode="showOnDemand" itemHeight="44" font="Regular;28" secondfont="Regular;28" backgroundColor="#011a2e" zPosition="1" />
        
        <!-- Interactive Functional Buttons -->
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/green.png" position="60,1000" size="40,40" alphatest="blend" zPosition="1" />
        <widget name="key_green" position="110,1000" size="250,40" font="Bold;28" halign="left" valign="center" transparent="1" foregroundColor="#FFFFFF" zPosition="1" />
        
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/yellow.png" position="360,1000" size="40,40" alphatest="blend" zPosition="1" />
        <widget name="key_yellow" position="410,1000" size="250,40" font="Bold;28" halign="left" valign="center" transparent="1" foregroundColor="#FFFFFF" zPosition="1" />
    </screen>"""

    def __init__(self, session, element, is_new):
        Screen.__init__(self, session)
        ConfigListScreen.__init__(self, [])
        self.session = session
        self.element = element
        self.is_new = is_new
        
        self["plugin_title"] = Label("..:: Ciefp Satellites.xml Parameters Editor ::..")
        self["background"] = Pixmap()
        self["key_green"] = Label("Save Changes")
        self["key_yellow"] = Label("Cycle Values")
        
        self.createConfig()
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.okPressed,
            "cancel": self.close,
            "green": self.save,
            "yellow": self.edit
        }, -1)
        
        self.onLayoutFinish.append(self.init_editor_assets)

    def init_editor_assets(self):
        img_path = "/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/satellitesxml2.png"
        if os.path.exists(img_path):
            self["background"].instance.setPixmapFromFile(img_path)

    def createConfig(self):
        self.config_list = []
        if self.is_new:
            self.frequency = ConfigInteger(default=0, limits=(0, 99999))
            self.symbol_rate = ConfigInteger(default=0, limits=(0, 99999))
            self.polarization = ConfigSelection(choices=POLARIZATION, default="0")
            self.fec_inner = ConfigSelection(choices=FEC_INNER, default="0")
            self.system = ConfigSelection(choices=SYSTEM, default="0")
            self.modulation = ConfigSelection(choices=MODULATION, default="0")
            self.is_id = ConfigInteger(default=0, limits=(0, 255))
            self.pls_code = ConfigInteger(default=0, limits=(0, 262141))
            self.pls_mode = ConfigSelection(choices=PLS_MODE, default="2")
            self.t2mi_plp_id = ConfigInteger(default=-1, limits=(-1, 255))
            self.t2mi_pid = ConfigInteger(default=0, limits=(0, 8192))
        else:
            self.frequency = ConfigInteger(default=int(self.element.get("frequency", "0")) // 1000, limits=(0, 99999))
            self.symbol_rate = ConfigInteger(default=int(self.element.get("symbol_rate", "0")) // 1000, limits=(0, 99999))
            self.polarization = ConfigSelection(choices=POLARIZATION, default=self.element.get("polarization", "0"))
            self.fec_inner = ConfigSelection(choices=FEC_INNER, default=self.element.get("fec_inner", "0"))
            self.system = ConfigSelection(choices=SYSTEM, default=self.element.get("system", "0"))
            self.modulation = ConfigSelection(choices=MODULATION, default=self.element.get("modulation", "0"))
            self.is_id = ConfigInteger(default=int(self.element.get("is_id", "0")), limits=(0, 255))
            self.pls_code = ConfigInteger(default=int(self.element.get("pls_code", "0")), limits=(0, 262141))
            self.pls_mode = ConfigSelection(choices=PLS_MODE, default=self.element.get("pls_mode", "2"))
            self.t2mi_plp_id = ConfigInteger(default=int(self.element.get("t2mi_plp_id", "-1")), limits=(-1, 255))
            self.t2mi_pid = ConfigInteger(default=int(self.element.get("t2mi_pid", "0")), limits=(0, 8192))

        self.config_list.append(getConfigListEntry("Frequency (MHz)", self.frequency))
        self.config_list.append(getConfigListEntry("Symbol Rate (kS/s)", self.symbol_rate))
        self.config_list.append(getConfigListEntry("Polarization orientation", self.polarization))
        self.config_list.append(getConfigListEntry("Forward Error Correction (FEC)", self.fec_inner))
        self.config_list.append(getConfigListEntry("DVB Broadcast System Type", self.system))
        self.config_list.append(getConfigListEntry("Signal Modulation Type", self.modulation))
        self.config_list.append(getConfigListEntry("Multistream Stream ID (0=Deactivated)", self.is_id))
        self.config_list.append(getConfigListEntry("Physical Layer Scrambling (PLS) Code", self.pls_code))
        self.config_list.append(getConfigListEntry("Physical Layer Scrambling (PLS) Mode", self.pls_mode))
        self.config_list.append(getConfigListEntry("T2-MI Packet Identifier PLP ID (-1=Disabled)", self.t2mi_plp_id))
        self.config_list.append(getConfigListEntry("T2-MI Baseband Processing PID", self.t2mi_pid))
        self["config"].list = self.config_list

    def okPressed(self):
        self.edit()

    def edit(self):
        self.keyRight()

    def save(self):
        if self.is_new:
            new_trans = ET.Element("transponder")
            new_trans.set("frequency", str(self.frequency.value * 1000))
            new_trans.set("symbol_rate", str(self.symbol_rate.value * 1000))
            new_trans.set("polarization", self.polarization.value)
            new_trans.set("fec_inner", self.fec_inner.value)
            new_trans.set("system", self.system.value)
            new_trans.set("modulation", self.modulation.value)
            
            if self.is_id.value > 0:
                new_trans.set("is_id", str(self.is_id.value))
                new_trans.set("pls_code", str(self.pls_code.value))
                new_trans.set("pls_mode", self.pls_mode.value)
            
            if self.t2mi_plp_id.value >= 0:
                new_trans.set("t2mi_plp_id", str(self.t2mi_plp_id.value))
                new_trans.set("t2mi_pid", str(self.t2mi_pid.value))
            
            transponders = self.element.findall("transponder")
            insert_index = 0
            new_freq = int(new_trans.get("frequency"))
            for i, trans in enumerate(transponders):
                trans_freq = int(trans.get("frequency", "0"))
                if new_freq < trans_freq:
                    break
                insert_index = i + 1
            
            self.element.insert(insert_index, new_trans)
            self.element = new_trans
        else:
            self.element.set("frequency", str(self.frequency.value * 1000))
            self.element.set("symbol_rate", str(self.symbol_rate.value * 1000))
            self.element.set("polarization", self.polarization.value)
            self.element.set("fec_inner", self.fec_inner.value)
            self.element.set("system", self.system.value)
            self.element.set("modulation", self.modulation.value)
            
            if self.is_id.value > 0:
                self.element.set("is_id", str(self.is_id.value))
                self.element.set("pls_code", str(self.pls_code.value))
                self.element.set("pls_mode", self.pls_mode.value)
            else:
                for attr in ["is_id", "pls_code", "pls_mode"]:
                    if attr in self.element.attrib:
                        del self.element.attrib[attr]
            
            if self.t2mi_plp_id.value >= 0:
                self.element.set("t2mi_plp_id", str(self.t2mi_plp_id.value))
                self.element.set("t2mi_pid", str(self.t2mi_pid.value))
            else:
                for attr in ["t2mi_plp_id", "t2mi_pid"]:
                    if attr in self.element.attrib:
                        del self.element.attrib[attr]
        
        self.close()

def main(session, **kwargs):
    session.open(CiefpSatelliteXmlReader)

def Plugins(**kwargs):
    return PluginDescriptor(
        name="{0} v{1}".format(PLUGIN_NAME, PLUGIN_VERSION),
        description="Edit satellites.xml file parameters",
        icon=PLUGIN_ICON,
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main
    )