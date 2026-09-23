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

PLUGIN_VERSION = "1.3"
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

# Dodaj ove konstante
TERRESTRIAL_XML_PATH = "/etc/tuxbox/terrestrial.xml"
TERRESTRIAL_XML_PATH_ENIGMA2 = "/etc/enigma2/terrestrial.xml"

# Dodaj ove mape za DVB-T parametre
BANDWIDTH = {
    "0": "8 MHz",
    "1": "7 MHz",
    "2": "6 MHz",
    "3": "Auto",
    "4": "5 MHz",
    "5": "1.712 MHz",
    "6": "10 MHz"
}

CONSTELLATION = {
    "0": "QPSK",
    "1": "16-QAM",
    "2": "64-QAM",
    "3": "Auto",
    "4": "256-QAM"
}

CODE_RATE = {
    "0": "1/2",
    "1": "2/3",
    "2": "3/4",
    "3": "5/6",
    "4": "7/8",
    "5": "Auto",
    "6": "None",
    "7": "8/9",
    "8": "3/5",
    "9": "4/5"
}

GUARD_INTERVAL = {
    "0": "1/32",
    "1": "1/16",
    "2": "1/8",
    "3": "1/4",
    "4": "Auto",
    "5": "Auto",
    "6": "6/4",
    "7": "8/9",
    "8": "3/5",
    "9": "4/5"
}

TRANSMISSION_MODE = {
    "0": "2K",
    "1": "8K",
    "2": "Auto",
    "3": "4K",
    "4": "1K",
    "5": "16K",
    "6": "32K"
}
# DVB-T kanali po frekvencijama (za 8MHz bandwidth)
DVB_T_CHANNELS = {
    177500000: "Ch 5",  # 177.5 MHz
    184500000: "Ch 6",  # 184.5 MHz
    191500000: "Ch 7",  # 191.5 MHz
    198500000: "Ch 8",  # 198.5 MHz
    205500000: "Ch 9",  # 205.5 MHz
    212500000: "Ch 10",  # 212.5 MHz
    219500000: "Ch 11",  # 219.5 MHz
    226500000: "Ch 12",  # 226.5 MHz
    474000000: "Ch 21",  # 474 MHz
    482000000: "Ch 22",  # 482 MHz
    490000000: "Ch 23",  # 490 MHz
    498000000: "Ch 24",  # 498 MHz
    506000000: "Ch 25",  # 506 MHz
    514000000: "Ch 26",  # 514 MHz
    522000000: "Ch 27",  # 522 MHz
    530000000: "Ch 28",  # 530 MHz
    538000000: "Ch 29",  # 538 MHz
    546000000: "Ch 30",  # 546 MHz
    554000000: "Ch 31",  # 554 MHz
    562000000: "Ch 32",  # 562 MHz
    570000000: "Ch 33",  # 570 MHz
    578000000: "Ch 34",  # 578 MHz
    586000000: "Ch 35",  # 586 MHz
    594000000: "Ch 36",  # 594 MHz
    602000000: "Ch 37",  # 602 MHz
    610000000: "Ch 38",  # 610 MHz
    618000000: "Ch 39",  # 618 MHz
    626000000: "Ch 40",  # 626 MHz
    634000000: "Ch 41",  # 634 MHz
    642000000: "Ch 42",  # 642 MHz
    650000000: "Ch 43",  # 650 MHz
    658000000: "Ch 44",  # 658 MHz
    666000000: "Ch 45",  # 666 MHz
    674000000: "Ch 46",  # 674 MHz
    682000000: "Ch 47",  # 682 MHz
    690000000: "Ch 48",  # 690 MHz
    698000000: "Ch 49",  # 698 MHz
    706000000: "Ch 50",  # 706 MHz
    714000000: "Ch 51",  # 714 MHz
    722000000: "Ch 52",  # 722 MHz
    730000000: "Ch 53",  # 730 MHz
    738000000: "Ch 54",  # 738 MHz
    746000000: "Ch 55",  # 746 MHz
    754000000: "Ch 56",  # 754 MHz
    762000000: "Ch 57",  # 762 MHz
    770000000: "Ch 58",  # 770 MHz
    778000000: "Ch 59",  # 778 MHz
    786000000: "Ch 60",  # 786 MHz
    794000000: "Ch 61",  # 794 MHz
    802000000: "Ch 62",  # 802 MHz
    810000000: "Ch 63",  # 810 MHz
    818000000: "Ch 64",  # 818 MHz
    826000000: "Ch 65",  # 826 MHz
    834000000: "Ch 66",  # 834 MHz
    842000000: "Ch 67",  # 842 MHz
    850000000: "Ch 68",  # 850 MHz
    858000000: "Ch 69",  # 858 MHz
}


def get_dvb_t_channel(frequency):
    """Vrati naziv kanala za datu frekvenciju"""
    # Pokušaj pronaći tačan kanal
    if frequency in DVB_T_CHANNELS:
        return DVB_T_CHANNELS[frequency]

    # Ako nije pronađen, pokušaj sa tolerancijom od 1MHz
    for freq, channel in DVB_T_CHANNELS.items():
        if abs(frequency - freq) < 1000000:  # tolerancija 1MHz
            return channel

    return "Unknown"


class CiefpSatelliteXmlReader(Screen):
    skin = """
    <screen name="CiefpSatelliteXmlReader" position="center,center" size="1920,1080"  backgroundColor="#011a2e">
        <widget name="separator0" position="0,5" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
        <widget name="plugin_title" position="0,10" size="1920,60" font="Bold;34" halign="center" backgroundColor="#012e01" foregroundColor="#00FF00" text="..:: Ciefp Satellites.xml Reader ::..  (Version{version})" />
        <widget source="list" render="Listbox" position="20,100" size="1400,900" scrollbarMode="showOnDemand" itemHeight="30" font="Regular;24" backgroundColor="#011a2e">
            <convert type="StringList" />
        </widget>
        <widget name="separator1" position="0,75" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
        <widget name="background" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/satellitesxml.png" position="1450,100" size="450,900" zPosition="1" />
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/red.png" position="100,1000" size="40,40" alphatest="blend" />
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/green.png" position="350,1000" size="40,40" alphatest="blend" />
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/yellow.png" position="600,1000" size="40,40" alphatest="blend" />
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/blue.png" position="850,1000" size="40,40" alphatest="blend" />
        <widget name="key_red" position="150,1000" size="150,40" font="Regular;24" halign="left" valign="center" transparent="1" />
        <widget name="key_green" position="400,1000" size="150,40" font="Regular;24" halign="left" valign="center" transparent="1" />
        <widget name="key_yellow" position="650,1000" size="150,40" font="Regular;24" halign="left" valign="center" transparent="1" />
        <widget name="key_blue" position="900,1000" size="150,40" font="Regular;24" halign="left" valign="center" transparent="1" />
        <widget name="version_info" position="10,10" size="200,30" font="Regular;18" halign="left" valign="top" transparent="1" foregroundColor="#888888" text="Version: {version}" />
    </screen>
    """.format(version=PLUGIN_VERSION)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.list = []
        self.tuner_type = self.getTunerType()  # Dodaj ovo
        self.xml_path = self.getXmlPath()  # Dodaj ovo

        # Dohvati info o trenutnom kanalu
        current_info = self.getCurrentChannelInfo()
        title_text = f"..:: Ciefp {self.getTitle()} ::.."
        if current_info and current_info != "No service":
            title_text += f" [{current_info}]"

        self["plugin_title"] = Label("..:: Ciefp Satellites.xml Reader ::..")
        self["list"] = List(self.list)
        self["background"] = Pixmap()
        self["key_red"] = Label("Delete")
        self["key_green"] = Label("Save")
        self["key_yellow"] = Label("Edit")
        self["key_blue"] = Label("Add")
        self["version_info"] = Label(f"Version: {PLUGIN_VERSION}")

        # Separatori
        self["separator0"] = Label()
        self["separator1"] = Label()
        self["separator2"] = Label()
        self["separator3"] = Label()

        
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
        self.loadXml()

    def getTunerType(self):
        """Odredi tip tunera trenutnog servisa"""
        service = self.session.nav.getCurrentService()
        if not service:
            print("[CiefpSatelliteXmlReader] No active service found")
            return "DVB-S"  # Default

        frontendInfo = service.frontendInfo()
        if not frontendInfo:
            print("[CiefpSatelliteXmlReader] No frontend info available")
            return "DVB-S"

        frontendData = frontendInfo.getAll(True)
        if not frontendData:
            return "DVB-S"

        tuner_type = frontendData.get("tuner_type", "DVB-S")
        print(f"[CiefpSatelliteXmlReader] Detected tuner type: {tuner_type}")
        return tuner_type

    def getXmlPath(self):
        """Vrati odgovarajući XML fajl prema tipu tunera"""
        if self.tuner_type == "DVB-T" or self.tuner_type == "DVB-T2":
            return TERRESTRIAL_XML_PATH
        else:
            return SATELLITES_XML_PATH

    def getTitle(self):
        """Vrati naslov prema tipu tunera"""
        if self.tuner_type == "DVB-T" or self.tuner_type == "DVB-T2":
            return f"Terrestrial.xml Reader (DVB-T/T2)"
        else:
            return f"Satellites.xml Reader (DVB-S/S2)"

    def loadXml(self):
        try:
            # Pokušaj učitati odgovarajući fajl
            if os.path.exists(self.xml_path):
                self.tree = ET.parse(self.xml_path)
                self.updateList()
                self.focusTimer.start(100, True)
            else:
                print(f"[CiefpSatelliteXmlReader] {self.xml_path} not found")
                self.session.open(MessageBox, f"{self.xml_path} not found!", MessageBox.TYPE_ERROR)
        except Exception as e:
            print(f"[CiefpSatelliteXmlReader] Error loading XML: {str(e)}")
            self.session.open(MessageBox, f"Error loading XML: {str(e)}", MessageBox.TYPE_ERROR)

    def getCurrentTerrestrialData(self):
        """Dohvati trenutne DVB-T/T2 podatke"""
        service = self.session.nav.getCurrentService()
        if not service:
            print("[CiefpSatelliteXmlReader] No active service found")
            return None

        frontendInfo = service.frontendInfo()
        if not frontendInfo:
            print("[CiefpSatelliteXmlReader] No frontend info available")
            return None

        frontendData = frontendInfo.getAll(True)
        if not frontendData:
            return None

        # DVB-T podaci
        data = {
            "frequency": frontendData.get("frequency", 0),  # u Hz
            "bandwidth": int(frontendData.get("bandwidth", 0)),
            "constellation": int(frontendData.get("constellation", 0)),
            "code_rate_hp": int(frontendData.get("code_rate_hp", 0)),
            "code_rate_lp": int(frontendData.get("code_rate_lp", 0)),
            "guard_interval": int(frontendData.get("guard_interval", 0)),
            "transmission_mode": int(frontendData.get("transmission_mode", 0)),
            "hierarchy_information": int(frontendData.get("hierarchy_information", 0)),
            "inversion": int(frontendData.get("inversion", 0)),
        }
        print(f"[CiefpSatelliteXmlReader] Current terrestrial data: {data}")
        return data

    def getServiceNameForFrequency(self, frequency_hz):
        """Dohvati ime servisa za datu frekvenciju - pojednostavljena verzija"""
        try:
            service = self.session.nav.getCurrentService()
            if not service:
                return None

            service_info = service.info()
            if not service_info:
                return None

            name = service_info.getName()
            if name:
                return name

            return None
        except Exception as e:
            print(f"[CiefpSatelliteXmlReader] Error: {str(e)}")
            return None

    def getServiceNameFromBouquet(self, frequency_hz):
        """Dohvati ime servisa iz bouquet liste"""
        try:
            from enigma import eServiceCenter, iServiceInformation

            service_center = eServiceCenter.getInstance()

            # Dohvati listu bouquet-a
            bouquet_root = service_center.list(eServiceReference(1, 0, 0, 0, 0, 0, 0))
            if not bouquet_root:
                return None

            # Iteracija kroz bouquet listu
            bouquet_list = []
            service_center.list(bouquet_root).addList(bouquet_list, eServiceCenter.List().addList)

            # Prođi kroz sve stavke u bouquet-u
            for service_ref in bouquet_list:
                if not service_ref:
                    continue

                # Provjeri da li je servis (ne folder)
                if service_ref.flags & eServiceReference.isGroup:
                    continue

                # Dohvati info o servisu
                service = service_center.info(service_ref)
                if not service:
                    continue

                try:
                    # Pokušaj dohvatiti frekvenciju
                    service_data = service.getAll(True)
                    if service_data:
                        service_freq = service_data.get("frequency", 0)
                        if abs(service_freq - frequency_hz) < 1000000:  # 1MHz tolerancija
                            name = service.getName(service_ref)
                            if name:
                                print(f"[CiefpSatelliteXmlReader] Found service: {name} on freq {service_freq}")
                                return name
                except:
                    pass

            return None
        except Exception as e:
            print(f"[CiefpSatelliteXmlReader] Error in bouquet: {str(e)}")
            return None

    def getCurrentChannelInfo(self):
        """Dohvati informacije o trenutnom kanalu"""
        service = self.session.nav.getCurrentService()
        if not service:
            return "No service"

        try:
            # Dohvati naziv kanala
            service_info = service.info()
            if service_info:
                name = service_info.getName()
                if name:
                    # Dohvati i frekvenciju
                    frontend_info = service.frontendInfo()
                    if frontend_info:
                        frontend_data = frontend_info.getAll(True)
                        if frontend_data:
                            freq = frontend_data.get("frequency", 0)
                            if freq:
                                freq_mhz = freq // 1000000
                                channel = get_dvb_t_channel(freq)
                                return f"{name} ({freq_mhz} MHz {channel})"
                    return name
        except:
            pass

        return "Unknown channel"

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
        if self.tuner_type == "DVB-T" or self.tuner_type == "DVB-T2":
            self.setFocusToCurrentTerrestrial()
        else:
            self.setFocusToCurrentSatellite()

    def setFocusToCurrentSatellite(self):
        """Originalna metoda za satelitske podatke"""
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
            self["list"].setList(self.list)
            self["list"].setIndex(found_index)

    def setFocusToCurrentTerrestrial(self):
        """Nova metoda za fokusiranje na DVB-T frekvenciju"""
        current_data = self.getCurrentTerrestrialData()
        if not current_data:
            print("[CiefpSatelliteXmlReader] No current terrestrial data")
            return

        found_index = -1
        current_terrestrial = None
        best_match_score = 0

        for idx, (text, elem) in enumerate(self.list):
            if elem.tag == "terrestrial":
                current_terrestrial = elem
            elif elem.tag == "transponder" and current_terrestrial:
                trans_freq = int(elem.get("centre_frequency", "0"))
                trans_bw = int(elem.get("bandwidth", "0"))
                trans_const = int(elem.get("constellation", "0"))
                trans_code_rate_hp = int(elem.get("code_rate_hp", "-1"))
                trans_guard = int(elem.get("guard_interval", "-1"))
                trans_mode = int(elem.get("transmission_mode", "-1"))

                # Izračunaj match score
                match_score = 0

                # Frekvencija (najvažnija) - tolerancija 1MHz
                freq_diff = abs(trans_freq - current_data["frequency"])
                if freq_diff < 1000000:  # 1MHz tolerancija
                    match_score += 100

                # Bandwidth
                if trans_bw == current_data["bandwidth"]:
                    match_score += 50

                # Constellation
                if trans_const == current_data["constellation"]:
                    match_score += 30

                # Code rate HP (ako postoji)
                if trans_code_rate_hp != -1 and trans_code_rate_hp == current_data.get("code_rate_hp", -1):
                    match_score += 20

                # Guard interval (ako postoji)
                if trans_guard != -1 and trans_guard == current_data.get("guard_interval", -1):
                    match_score += 20

                # Transmission mode (ako postoji)
                if trans_mode != -1 and trans_mode == current_data.get("transmission_mode", -1):
                    match_score += 20

                print(f"[CiefpSatelliteXmlReader] Match score for {trans_freq}: {match_score}")

                # Ako je ovo najbolji match do sada
                if match_score > best_match_score:
                    best_match_score = match_score
                    found_index = idx

                    # Ako imamo savršen match (frekvencija se poklapa), prekini
                    if freq_diff < 1000000 and match_score >= 100:
                        print(f"[CiefpSatelliteXmlReader] Perfect match found at index {idx}: {text}")
                        break

        if found_index != -1 and found_index < len(self.list):
            self["list"].setList(self.list)
            self["list"].setIndex(found_index)
            print(f"[CiefpSatelliteXmlReader] Set focus to index {found_index}")
        else:
            print("[CiefpSatelliteXmlReader] No terrestrial match found")

    def updateList(self):
        self.list = []
        root = self.tree.getroot()

        # Dohvati trenutnu frekvenciju i ime kanala JEDNOM
        current_freq = None
        current_name = None
        try:
            service = self.session.nav.getCurrentService()
            if service:
                frontend_info = service.frontendInfo()
                if frontend_info:
                    frontend_data = frontend_info.getAll(True)
                    if frontend_data:
                        current_freq = frontend_data.get("frequency", 0)
                        service_info = service.info()
                        if service_info:
                            current_name = service_info.getName()
        except Exception as e:
            print(f"[CiefpSatelliteXmlReader] Error getting current service: {str(e)}")

        if self.tuner_type == "DVB-T" or self.tuner_type == "DVB-T2":
            # DVB-T/T2 prikaz
            for terrestrial in root.findall("terrestrial"):
                name = terrestrial.get("name", "Unknown")
                flags = terrestrial.get("flags", "0")
                self.list.append((f"Terrestrial: {name} (flags={flags})", terrestrial))

                for trans in terrestrial.findall("transponder"):
                    freq_hz = int(trans.get("centre_frequency", "0"))
                    freq_mhz = freq_hz // 1000000
                    channel = get_dvb_t_channel(freq_hz)
                    bw = BANDWIDTH.get(trans.get("bandwidth", "0"), "Unknown")
                    const = CONSTELLATION.get(trans.get("constellation", "0"), "Unknown")

                    # PROVJERI DA LI JE OVO TRENUTNA FREKVENCIJA
                    service_name = None
                    if current_freq is not None and current_name:
                        if abs(current_freq - freq_hz) < 1000000:  # 1MHz tolerancija
                            service_name = current_name
                            print(f"[CiefpSatelliteXmlReader] Match found: {service_name} on {freq_hz}")

                    # Dodatni parametri
                    extra = []
                    code_rate_hp = trans.get("code_rate_hp")
                    code_rate_lp = trans.get("code_rate_lp")
                    guard = trans.get("guard_interval")
                    mode = trans.get("transmission_mode")
                    hierarchy = trans.get("hierarchy_information")
                    inversion = trans.get("inversion")

                    if code_rate_hp:
                        extra.append(f"HP: {CODE_RATE.get(code_rate_hp, 'Unknown')}")
                    if code_rate_lp:
                        extra.append(f"LP: {CODE_RATE.get(code_rate_lp, 'Unknown')}")
                    if guard:
                        extra.append(f"GI: {GUARD_INTERVAL.get(guard, 'Unknown')}")
                    if mode:
                        extra.append(f"Mode: {TRANSMISSION_MODE.get(mode, 'Unknown')}")
                    if hierarchy:
                        extra.append(f"Hier: {hierarchy}")
                    if inversion:
                        extra.append(f"Inversion: {inversion}")

                    # Prikaz sa kanalom i imenom servisa (SAMO za trenutnu frekvenciju)
                    if service_name:
                        display_text = f"  TR: {freq_mhz} MHz {channel} | {service_name} | BW: {bw} | Const: {const}"
                    else:
                        display_text = f"  TR: {freq_mhz} MHz {channel} | BW: {bw} | Const: {const}"

                    if extra:
                        display_text += f" [{', '.join(extra)}]"

                    self.list.append((display_text, trans))
        else:
            # DVB-S/S2 prikaz (ostaje isti)
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
                        extra.append(
                            f"MIS: is_id={is_id}, pls_mode={PLS_MODE.get(pls_mode, 'Unknown')}, pls_code={pls_code}")
                    if t2mi_plp_id and int(t2mi_plp_id) >= 0:
                        extra.append(f"T2-MI: plp_id={t2mi_plp_id}, pid={t2mi_pid or '0'}")

                    display_text = f"  TR: {freq} {pol} {sr} {fec} {sys} {mod}"
                    if extra:
                        display_text += f" [{' | '.join(extra)}]"

                    self.list.append((display_text, trans))

        self["list"].setList(self.list)
        print(f"[CiefpSatelliteXmlReader] List populated with {len(self.list)} items")

    def okPressed(self):
        self.editLine()

    def deleteLine(self):
        cur = self["list"].getCurrent()
        if cur and isinstance(cur[1], ET.Element):
            root = self.tree.getroot()
            if cur[1].tag == "sat":
                root.remove(cur[1])
            elif cur[1].tag == "transponder":
                for sat in root.findall("sat"):
                    for trans in sat.findall("transponder"):
                        if trans == cur[1]:
                            sat.remove(trans)
                            break
                    else:
                        continue
                    break
            self.updateList()

    def saveChanges(self):
        try:
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

            # Spremi na originalnu lokaciju
            with open(self.xml_path, 'w', encoding='iso-8859-1') as f:
                f.write(final_xml)
            print(f"[CiefpSatelliteXmlReader] Saved to {self.xml_path}")

            # Spremi i na drugu lokaciju ako je satelitski
            if self.tuner_type == "DVB-S" or self.tuner_type == "DVB-S2":
                try:
                    with open(SATELLITES_XML_PATH_ENIGMA2, 'w', encoding='iso-8859-1') as f:
                        f.write(final_xml)
                    print(f"[CiefpSatelliteXmlReader] Saved to {SATELLITES_XML_PATH_ENIGMA2}")
                except Exception as e:
                    print(f"[CiefpSatelliteXmlReader] Error saving to {SATELLITES_XML_PATH_ENIGMA2}: {str(e)}")

            self.session.open(MessageBox, f"Changes saved successfully to {self.xml_path}!", MessageBox.TYPE_INFO)
        except Exception as e:
            print(f"[CiefpSatelliteXmlReader] Error saving XML: {str(e)}")
            self.session.open(MessageBox, f"Error saving XML: {str(e)}", MessageBox.TYPE_ERROR)

    def editLine(self):
        cur = self["list"].getCurrent()
        if cur and isinstance(cur[1], ET.Element) and cur[1].tag == "transponder":
            self.session.open(CiefpSatelliteXmlEditor, cur[1], False)

    def addLine(self):
        cur = self["list"].getCurrent()
        if cur and isinstance(cur[1], ET.Element) and cur[1].tag == "sat":
            self.session.open(CiefpSatelliteXmlEditor, cur[1], True)


class CiefpSatelliteXmlEditor(ConfigListScreen, Screen):
    skin = """
    <screen name="CiefpSatelliteXmlEditor" position="center,center" size="1920,1080"  backgroundColor="#011a2e">
        <widget name="title" render="Label" position="100,80" size="1600,60" font="Regular;34" halign="center" valign="center" foregroundColor="#00FF00" text="..:: Ciefp Satellites.xml Editor ::..  (Version{version})" backgroundColor="#050505" zPosition="3" />
        <widget name="config" position="100,150" size="1000,720" scrollbarMode="showOnDemand" itemHeight="36" font="Regular;26"  backgroundColor="#012e01" />
        <widget name="background" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/satellitesxml2.png" position="1100,150" size="600,800" zPosition="0" />
        <widget name="title2" render="Label" position="100,870" size="1000,80" font="Regular;34" halign="center" valign="center" foregroundColor="#ffffff" backgroundColor="#050505" zPosition="2" />
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/red.png" position="100,900" size="40,40" alphatest="blend" zPosition="2" />
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/green.png" position="350,900" size="40,40" alphatest="blend" zPosition="2" />
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/yellow.png" position="600,900" size="40,40" alphatest="blend" zPosition="2" />
        <ePixmap pixmap="/usr/share/enigma2/skin_default/buttons/blue.png" position="850,900" size="40,40" alphatest="blend" zPosition="2" />
        <widget name="key_red" position="150,900" size="150,40" font="Regular;24" halign="left" valign="center" backgroundColor="#050505" zPosition="2" />
        <widget name="key_green" position="400,900" size="150,40" font="Regular;24" halign="left" valign="center" backgroundColor="#050505" zPosition="2" />
        <widget name="key_yellow" position="650,900" size="150,40" font="Regular;24" halign="left" valign="center" backgroundColor="#050505" zPosition="2" />
        <widget name="key_blue" position="900,900" size="150,40" font="Regular;24" halign="left" valign="center" backgroundColor="#050505" zPosition="2" />
    </screen>
    """.format(version=PLUGIN_VERSION)

    def __init__(self, session, element, is_new):
        Screen.__init__(self, session)
        ConfigListScreen.__init__(self, [])
        self.session = session
        self.element = element
        self.is_new = is_new
        self["title"] = Label("..:: Ciefp Satellites.xml Editor ::..")
        self["title2"] = Label("")
        self["background"] = Pixmap()
        self["key_red"] = Label("Exit")
        self["key_green"] = Label("Save")
        self["key_yellow"] = Label("Edit")
        self["key_blue"] = Label("Scan")
        self["version_info"] = Label(f"Version: {PLUGIN_VERSION}")
        self.createConfig()
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.okPressed,
            "cancel": self.close,
            "red": self.exitPressed,
            "green": self.save,
            "yellow": self.edit,
            "blue": self.scanPressed
        }, -1)

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
            self.symbol_rate = ConfigInteger(default=int(self.element.get("symbol_rate", "0")) // 1000,
                                             limits=(0, 99999))
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
        self.config_list.append(getConfigListEntry("Polarization", self.polarization))
        self.config_list.append(getConfigListEntry("FEC", self.fec_inner))
        self.config_list.append(getConfigListEntry("System", self.system))
        self.config_list.append(getConfigListEntry("Modulation", self.modulation))
        self.config_list.append(getConfigListEntry("Multistream ID (0=off)", self.is_id))
        self.config_list.append(getConfigListEntry("PLS Code", self.pls_code))
        self.config_list.append(getConfigListEntry("PLS Mode", self.pls_mode))
        self.config_list.append(getConfigListEntry("T2-MI PLP ID (-1=off)", self.t2mi_plp_id))
        self.config_list.append(getConfigListEntry("T2-MI PID", self.t2mi_pid))
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

            # Pronađi ispravnu poziciju za umetanje prema frekvenciji
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

    def exitPressed(self):
        """Crveno dugme - zatvara editor bez spremanja"""
        self.close()

    def scanPressed(self):
        """Plavo dugme - otvara Signal Finder"""
        service = self.session.nav.getCurrentService()
        if service:
            self.session.open(ScanSetup)
        else:
            self.session.open(MessageBox, "Please select a service first!", MessageBox.TYPE_INFO)


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