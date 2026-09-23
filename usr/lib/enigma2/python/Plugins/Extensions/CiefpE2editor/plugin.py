from __future__ import absolute_import
from .plugin_channel_editor import CiefpChannelEditor, CiefpBouquetEditor, CiefpChannelManager
from .plugin_select_satellite import CiefpSelectSatellite
from .plugin_settings_downloader import CiefpSettingsDownloaderScreen
from .plugin_satellites_xml_editor import CiefpSatelliteXmlReader
from .plugin_settings_motor import CiefpSettingsScreen
from .plugin_3 import WhitelistScreen
from .plugin_comparison import CiefpComparisonScreen   # ← NOVO
from .plugin_ciefpsignalinfo import CiefpSignalInfoScreen
from .plugin_caid_manager import CiefpCAIDManager
from Plugins.Plugin import PluginDescriptor
import os
import re
import xml.etree.ElementTree as ET
from enigma import eDVBDB
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import fileExists

# Globalne varijable
PLUGIN_VERSION = "2.2"
PLUGIN_NAME = "CiefpE2editor"
PLUGIN_ICON = "icon.png"

debug_file = "/tmp/ciefp_e2editor_debug.log"


def log_debug(message):
    try:
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(f"{message}\n")
    except:
        pass


class CiefpE2editorMain(Screen):
    """Glavni ekran sa bezbednim čuvanjem IPTV/StreamRelay kanala i popravljenim filterom satelita"""

    skin = """
        <screen position="center,center" size="1920,1080" backgroundColor="#011a2e">
            <!-- Titule -->
            <widget name="separator0" position="0,5" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />  
            <widget name="plugin_title" position="0,10" size="1920,40" font="Bold;30" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="..:: Ciefp E2 Editor ::.." />
            <widget name="service_title" position="10,50" size="450,35" font="Bold;30" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="Service" />
            <widget name="channel_title" position="460,50" size="900,35" font="Bold;30" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="Channels" />
            <widget name="bouquet_title" position="1360,50" size="530,35" font="Bold;30" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="Bouquets" />
            <widget name="separator1" position="0,87" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
            <!-- Liste -->
            <widget name="service_list" position="20,90" size="450,858" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;26" backgroundColor="#011a2e" />
            <widget name="channel_list" position="470,90" size="900,858" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;26" backgroundColor="#011a2e" />
            <widget name="bouquet_list" position="1390,90" size="530,858" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;26" backgroundColor="#011a2e" />

            <!-- Status -->
            <widget name="separator2" position="0,950" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
            <widget name="status" position="10,950" size="1900,40" font="Regular;24"  backgroundColor="#011a2e" foregroundColor="#00FF00" />
            <widget name="separator2" position="0,990" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
            <!-- Dugmad -->
            <widget name="red_button" position="10,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#9F1313" foregroundColor="#FFFFFF" text="Exit" />
            <widget name="green_button" position="370,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#1F771F" foregroundColor="#FFFFFF" text="Satellite" />
            <widget name="yellow_button" position="740,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#9F9F13" foregroundColor="#000000" text="Filters Menu" />
            <widget name="blue_button" position="1110,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#1F1F77" foregroundColor="#FFFFFF" text="Bouquets" />
            <widget name="menu_button" position="1480,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#777777" foregroundColor="#FFFFFF" text="MENU" />

            <!-- Info -->
            <widget name="info" position="900,950" size="900,40" font="Regular;30" halign="right" foregroundColor="#00FF00" backgroundColor="#011a2e" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        # Inicijalizacija listi
        self["service_list"] = MenuList([])
        self["channel_list"] = MenuList([])
        self["bouquet_list"] = MenuList([])

        # Titule
        self["plugin_title"] = Label("..:: Ciefp E2 Editor ::..")
        self["service_title"] = Label("Service")
        self["channel_title"] = Label("Channels")
        self["bouquet_title"] = Label("Bouquets")

        # Status i info
        self["status"] = Label("Loading...")
        self["info"] = Label(f"v{PLUGIN_VERSION}")

        # Dugmad
        self["red_button"] = Label("Exit")
        self["green_button"] = Label("Satellite")
        self["yellow_button"] = Label("Filters Menu")
        self["blue_button"] = Label("Bouquets")
        self["menu_button"] = Label("MENU")

        # Separatori
        self["separator0"] = Label()
        self["separator1"] = Label()
        self["separator2"] = Label()
        self["separator3"] = Label()

        # Podaci
        self.all_services = []
        self.filtered_services = []
        self.service_refs = {}  
        self.bouquet_names = {}  
        self.bouquet_files = {}  
        self.channel_refs = {}
        self.current_bouquet = None
        self.current_bouquet_file = None

        # Glavni Selektovani Filteri
        self.current_satellite = "All Satellite"
        self.filter_mode = "All"  
        self.selected_provider = None

        # Akcije
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"],
            {
                "ok": self.ok_pressed,
                "cancel": self.exit,
                "up": self.move_up,
                "down": self.move_down,
                "left": self.move_left,
                "right": self.move_right,
                "red": self.exit,
                "green": self.satellite_filter,
                "yellow": self.main_filter_menu, 
                "blue": self.bouquet_filter,
                "menu": self.open_move_editor,
            },
            -1
        )

        self.active_panel = 0
        self.onLayoutFinish.append(self.init_data)

    def update_panel_focus(self):
        try:
            if self.active_panel == 0:
                self["status"].setText("Focus: Service panel | OK for Options")
            elif self.active_panel == 1:
                self["status"].setText("Focus: Channels panel | OK to Remove / Save")
            elif self.active_panel == 2:
                self["status"].setText("Focus: Bouquets panel | OK to load bouquet")
        except Exception as e:
            log_debug(f"Error in update_panel_focus: {str(e)}")

    def move_left(self):
        if self.active_panel > 0:
            self.active_panel -= 1
            self.update_panel_focus()

    def move_right(self):
        if self.active_panel < 2:
            self.active_panel += 1
            self.update_panel_focus()

    def move_up(self):
        if self.active_panel == 0:
            self["service_list"].up()
        elif self.active_panel == 1:
            self["channel_list"].up()
        elif self.active_panel == 2:
            self["bouquet_list"].up()

    def move_down(self):
        if self.active_panel == 0:
            self["service_list"].down()
        elif self.active_panel == 1:
            self["channel_list"].down()
        elif self.active_panel == 2:
            self["bouquet_list"].down()

    def ok_pressed(self):
        if self.active_panel == 0:
            current_service = self["service_list"].getCurrent()
            if not current_service:
                return

            options = [
                ("Copy to Active Bouquet", "copy"),
                ("Delete from Service List", "delete"),
                ("Save & Reload Settings", "save")
            ]

            self.session.openWithCallback(
                self.choicebox_callback,
                ChoiceBox,
                title=f"Options for Service: {current_service}",
                list=options
            )

        elif self.active_panel == 1:
            current_channel = self["channel_list"].getCurrent()
            if not current_channel:
                return

            options = [
                ("Remove from Bouquet", "remove_from_bouquet"),
                ("Save & Reload Settings", "save")
            ]

            self.session.openWithCallback(
                self.channel_choicebox_callback,
                ChoiceBox,
                title=f"Manage Bouquet Channel: {current_channel}",
                list=options
            )

        elif self.active_panel == 2:
            current_bouquet_name = self["bouquet_list"].getCurrent()
            if current_bouquet_name:
                self.current_bouquet = current_bouquet_name
                self.current_bouquet_file = self.bouquet_names.get(current_bouquet_name)
                if self.current_bouquet_file:
                    self.load_bouquet_channels(self.current_bouquet_file)
                    self["status"].setText(f"Loaded bouquet: {current_bouquet_name}")
                    self.active_panel = 1
                    self.update_panel_focus()

    def choicebox_callback(self, answer):
        if not answer:
            return
        action = answer[1]
        if action == "copy":
            self.copy_service_to_bouquet()
        elif action == "delete":
            self.delete_selected_service()
        elif action == "save":
            self.save_and_reload()

    def channel_choicebox_callback(self, answer):
        if not answer:
            return
        action = answer[1]
        current_channel = self["channel_list"].getCurrent()

        if action == "remove_from_bouquet":
            if current_channel:
                current_list = self["channel_list"].list
                if current_channel in current_list:
                    current_list.remove(current_channel)
                    self["channel_list"].setList(current_list)
                    if current_channel in self.channel_refs:
                        del self.channel_refs[current_channel]
                    self["status"].setText(f"Removed '{current_channel}' from active bouquet.")
        elif action == "save":
            self.save_and_reload()

    def copy_service_to_bouquet(self):
        service_name = self["service_list"].getCurrent()
        if not service_name:
            return

        if not self.current_bouquet_file:
            self.session.open(MessageBox, "Please open a bouquet first via the right panel or Blue button.", MessageBox.TYPE_ERROR)
            return

        service_ref = None
        for service in self.all_services:
            if service['name'] == service_name:
                if self.current_satellite != "All Satellite":
                    if self.current_satellite == "Terrestrial" and service['satellite'] != "Terrestrial":
                        continue
                    elif self.current_satellite != "Terrestrial" and self.current_satellite not in service['satellite']:
                        continue
                service_ref = service['ref']
                break

        if not service_ref:
            service_ref = self.service_refs.get(service_name)

        if not service_ref:
            final_bouquet_ref = "#SERVICE 1:0:1:0:0:0:0:0:0:0:"
        else:
            if service_ref.count(":") < 5:
                try:
                    parts = service_ref.split(":")
                    sid = parts[0].upper().lstrip('0') or "0"
                    satfreq = parts[1].upper().lstrip('0') or "0"
                    tsid = parts[2].upper().lstrip('0') or "0"
                    onid = parts[3].upper().lstrip('0') or "0"
                    
                    srv_type = "1"
                    for s in self.all_services:
                        if s['name'] == service_name and s['type'] == "Radio":
                            srv_type = "2"
                            break

                    final_bouquet_ref = f"#SERVICE 1:0:{srv_type}:{sid}:{tsid}:{onid}:{satfreq}:0:0:0:"
                except Exception as e:
                    final_bouquet_ref = f"#SERVICE 1:0:1:0:0:0:0:0:0:0:"
            else:
                if not service_ref.startswith("#SERVICE"):
                    final_bouquet_ref = f"#SERVICE {service_ref}"
                else:
                    final_bouquet_ref = service_ref

                if not final_bouquet_ref.endswith(":"):
                    final_bouquet_ref += ":"

        current_center_list = self["channel_list"].list
        if service_name in current_center_list:
            self["status"].setText("Channel already exists in this bouquet!")
            return

        current_center_list.append(service_name)
        self["channel_list"].setList(current_center_list)
        self.channel_refs[service_name] = final_bouquet_ref
        self["status"].setText(f"Copied '{service_name}' to active bouquet.")

    def delete_selected_service(self):
        service_name = self["service_list"].getCurrent()
        if service_name:
            current_list = self["service_list"].list
            if service_name in current_list:
                current_list.remove(service_name)
                self["service_list"].setList(current_list)
                self.all_services = [s for s in self.all_services if s['name'] != service_name]
                self["status"].setText(f"Deleted '{service_name}' from view.")

    def save_and_reload(self):
        if self.current_bouquet_file:
            bouquet_path = os.path.join("/etc/enigma2", self.current_bouquet_file)
            try:
                new_lines = []
                new_lines.append(f"#NAME {self.current_bouquet}\n")

                for channel in self["channel_list"].list:
                    line = self.channel_refs.get(channel)
                    
                    if line:
                        if not line.startswith("#SERVICE"):
                            line = f"#SERVICE {line}"
                        new_lines.append(line + "\n")
                        
                        if " (IPTV)" in channel or " (StreamRelay)" in channel:
                            clean_desc = channel.replace(" (StreamRelay)", "").replace(" (IPTV)", "")
                            new_lines.append(f"#DESCRIPTION {clean_desc}\n")
                        continue

                    if channel.startswith("[") and channel.endswith("]"):
                        marker_clean = channel[1:-1]
                        new_lines.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n#DESCRIPTION {marker_clean}\n")

                with open(bouquet_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)

                eDVBDB.getInstance().reloadServicelist()
                eDVBDB.getInstance().reloadBouquets()

                self.session.open(MessageBox, "Settings saved and reloaded successfully!", MessageBox.TYPE_INFO, timeout=3)
                self["status"].setText("Saved and reloaded.")
            except Exception as e:
                self.session.open(MessageBox, f"Save failed: {str(e)}", MessageBox.TYPE_ERROR)

    def init_data(self):
        self["status"].setText("Loading data...")
        self.load_all_services()
        self.load_all_bouquets()

        if self.bouquet_names:
            first_bouquet = list(self.bouquet_names.keys())[0]
            self.current_bouquet = first_bouquet
            self.current_bouquet_file = self.bouquet_names[first_bouquet]
            self.load_bouquet_channels(self.current_bouquet_file)

        self.update_panel_focus()

    def load_all_services(self):
        self.all_services = []
        self.service_refs = {}

        lamedb_services, service_metadata = self.parse_lamedb()

        for ref, name in lamedb_services.items():
            if name and not name.startswith("p:"):
                self.service_refs[ref] = name
                meta = service_metadata.get(ref, {"type": "1", "provider": "Unknown", "new_flag": False})
                
                service_info = self.parse_service_ref(ref, name, meta["type"], meta["provider"], meta["new_flag"])
                if service_info:
                    self.all_services.append(service_info)

        self.apply_filters()

    def parse_lamedb(self):
        lamedb_path = "/etc/enigma2/lamedb"
        services = {}
        service_metadata = {}

        if not os.path.exists(lamedb_path):
            return services, service_metadata

        try:
            with open(lamedb_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            start_idx = content.find("\nservices\n")
            end_idx = content.find("\nend\n", start_idx)
            if start_idx == -1 or end_idx == -1:
                return services, service_metadata
                
            services_block = content[start_idx + 10:end_idx]
            lines = services_block.splitlines()
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                
                if ":" in line and not line.startswith("p:") and not line.startswith("c:"):
                    parts = line.split(":")
                    if len(parts) >= 5:
                        sid = parts[0]
                        satfreq = parts[1].lower()
                        tsid = parts[2]
                        onid = parts[3]
                        srv_type = parts[4]

                        key1 = f"{sid}:{satfreq}:{tsid}:{onid}"
                        key2 = f"{sid.lstrip('0') or '0'}:{satfreq}:{tsid.lstrip('0') or '0'}:{onid.lstrip('0') or '0'}"
                        
                        name = ""
                        if i + 1 < len(lines):
                            name = lines[i+1].strip()
                        
                        provider_name = "Unknown"
                        has_new_flag = False
                        
                        if i + 2 < len(lines):
                            extra_line = lines[i+2].strip()
                            if extra_line.startswith("p:") or "f:" in extra_line:
                                p_match = re.search(r'p:([^,]+)', extra_line)
                                if p_match:
                                    provider_name = p_match.group(1).strip()
                                
                                if "f:40" in extra_line or ",f:40" in extra_line:
                                    has_new_flag = True
                        
                        if name and not name.startswith("p:") and not name.startswith("c:"):
                            services[key1] = name
                            services[key2] = name
                            
                            meta = {"type": srv_type, "provider": provider_name, "new_flag": has_new_flag}
                            service_metadata[key1] = meta
                            service_metadata[key2] = meta
                            
                        i += 2
                        continue
                i += 1
        except Exception as e:
            log_debug(f"Error parsing lamedb: {str(e)}")

        return services, service_metadata

    def parse_service_ref(self, ref, name, srv_type_code="1", provider="Unknown", new_flag=False):
        try:
            parts = ref.split(":")
            if len(parts) >= 4:
                sid = parts[0].upper()
                raw_ns = parts[1].upper()
                namespace = raw_ns.zfill(8) if len(raw_ns) > 4 else raw_ns + "0000"
                tsid = parts[2].upper()
                onid = parts[3].upper()

                ns_key = namespace[:4].upper()
                if ns_key.startswith("EEEE"):
                    satellite = "Terrestrial"
                elif ns_key.startswith("FFFF"):
                    satellite = "Cable"
                else:
                    try:
                        ns_val = int(ns_key, 16)
                        if ns_val < 0x708:
                            deg = ns_val / 10.0
                            satellite = f"{deg:.1f}°E".replace(".0°E", "°E")
                        else:
                            deg = (3600 - ns_val) / 10.0
                            satellite = f"{deg:.1f}°W".replace(".0°W", "°W")
                    except:
                        satellite = "Unknown"

                resolution = "SD"
                service_general_type = "TV"

                if srv_type_code in ["2", "10", "a", "A"]:
                    service_general_type = "Radio"
                    resolution = "Radio"
                elif srv_type_code == "32":
                    resolution = "UHD"
                elif srv_type_code == "31":
                    name_upper = name.upper()
                    if "UHD" in name_upper or "4K" in name_upper or "ULTRA HD" in name_upper:
                        resolution = "UHD"
                    else:
                        resolution = "HD_H265"
                elif srv_type_code in ["17", "25"]:
                    resolution = "HD_H264"
                else:
                    resolution = "SD"

                return {
                    'name': name,
                    'ref': ref,
                    'sid': sid,
                    'satfreq': namespace,
                    'tsid': tsid,
                    'onid': onid,
                    'satellite': satellite,
                    'type': service_general_type,
                    'resolution': resolution,
                    'provider': provider,
                    'new_channel': new_flag
                }
        except Exception as e:
            log_debug(f"Error in parse_service_ref: {str(e)}")
        return None

    def apply_filters(self):
        self.filtered_services = []
        
        for service in self.all_services:
            if self.current_satellite != "All Satellite":
                if self.current_satellite == "Terrestrial" and service['satellite'] != "Terrestrial":
                    continue
                elif self.current_satellite != "Terrestrial" and self.current_satellite not in service['satellite']:
                    continue
            
            if self.filter_mode == "TV" and service['type'] != "TV":
                continue
            elif self.filter_mode == "Radio" and service['type'] != "Radio":
                continue
            elif self.filter_mode == "SD" and (service['type'] != "TV" or service['resolution'] != "SD"):
                continue
            elif self.filter_mode == "HD_H264" and (service['type'] != "TV" or service['resolution'] != "HD_H264"):
                continue
            elif self.filter_mode == "HD_H265" and (service['type'] != "TV" or service['resolution'] != "HD_H265"):
                continue
            elif self.filter_mode == "UHD" and (service['type'] != "TV" or service['resolution'] != "UHD"):
                continue
            elif self.filter_mode == "NewChannels" and not service['new_channel']:
                continue
            elif self.filter_mode == "Provider" and service['provider'] != self.selected_provider:
                continue
            
            self.filtered_services.append(service['name'])
        
        self.filtered_services = sorted(list(set(self.filtered_services)))
        self["service_list"].setList(self.filtered_services)

    def main_filter_menu(self):
        choices = [
            ("Show All Services (- all types -)", "All"),
            ("TV Channels Only", "TV"),
            ("Radio Channels Only", "Radio"),
            ("TV (only SD)", "SD"),
            ("TV (only HD [H.264])", "HD_H264"),
            ("TV (only HD [H.265])", "HD_H265"),
            ("TV (only UHD [H.265])", "UHD"),
            ("Filter by New Channels (Flag X)", "NewChannels"),
            (f"Filter by Provider ({self.current_satellite})...", "Provider_Select")
        ]
        self.session.openWithCallback(
            self.main_filter_selected,
            ChoiceBox,
            title="Advanced Service Filters",
            list=choices
        )

    def main_filter_selected(self, choice):
        if not choice:
            return
        mode = choice[1]
        if mode == "Provider_Select":
            self.open_provider_sub_menu()
        else:
            self.filter_mode = mode
            self.apply_filters()
            self["status"].setText(f"Filter Mode: {choice[0]}")

    def open_provider_sub_menu(self):
        active_providers = set()

        for service in self.all_services:
            if self.current_satellite != "All Satellite":
                if self.current_satellite == "Terrestrial" and service['satellite'] != "Terrestrial":
                    continue
                elif self.current_satellite != "Terrestrial" and self.current_satellite not in service['satellite']:
                    continue
            
            if service['provider'] and service['provider'] != "Unknown":
                active_providers.add(service['provider'])

        if not active_providers:
            self.session.open(MessageBox, f"No providers found for: {self.current_satellite}!", MessageBox.TYPE_INFO, timeout=3)
            return
            
        choices = []
        sorted_providers = sorted(list(active_providers))
        for prov in sorted_providers:
            choices.append((prov, prov))
            
        self.session.openWithCallback(
            self.provider_selected_callback,
            ChoiceBox,
            title=f"Providers on {self.current_satellite}",
            list=choices
        )

    def provider_selected_callback(self, choice):
        if choice and choice[1]:
            self.filter_mode = "Provider"
            self.selected_provider = choice[1]
            self.apply_filters()
            self["status"].setText(f"Provider: {self.selected_provider} ({self.current_satellite})")

    def load_bouquet_channels(self, bouquet_file):
        self.channel_refs = {}
        bouquet_path = os.path.join("/etc/enigma2", bouquet_file)
        if not os.path.exists(bouquet_path):
            self["channel_list"].setList([])
            return

        lamedb_services, _ = self.parse_lamedb()
        channel_list = []
        try:
            with open(bouquet_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue

                if line.startswith("#NAME"):
                    i += 1
                    continue
                
                elif line.startswith("#SERVICE"):
                    if "http%3a//0.0.0.0%3a9999/" in line or "%3a9999" in line:
                        channel_name = "Unknown StreamRelay"
                        url_parts = line.split(":")
                        if len(url_parts) >= 11 and url_parts[10] and not url_parts[10].startswith("http"):
                            channel_name = url_parts[10]
                        
                        if i + 1 < len(lines) and lines[i+1].strip().startswith("#DESCRIPTION"):
                            desc_line = lines[i+1].strip()
                            channel_name = desc_line.replace("#DESCRIPTION", "").strip()
                            i += 1 

                        display_name = f"{channel_name} (StreamRelay)"
                        channel_list.append(display_name)
                        self.channel_refs[display_name] = line
                        i += 1
                        continue

                    elif line.startswith("#SERVICE 4097:") or line.startswith("#SERVICE 5001:") or line.startswith("#SERVICE 5002:") or "http" in line.lower():
                        channel_name = "Unknown IPTV"
                        url_parts = line.split(":")
                        if len(url_parts) >= 11 and url_parts[10]:
                            channel_name = url_parts[10]
                            
                        if i + 1 < len(lines) and lines[i+1].strip().startswith("#DESCRIPTION"):
                            desc_line = lines[i+1].strip()
                            channel_name = desc_line.replace("#DESCRIPTION", "").strip()
                            i += 1

                        display_name = f"{channel_name} (IPTV)"
                        channel_list.append(display_name)
                        self.channel_refs[display_name] = line
                        i += 1
                        continue

                    else:
                        parts = line.split(":")
                        if len(parts) >= 10:
                            if parts[1] == "64":  
                                if i + 1 < len(lines) and lines[i+1].strip().startswith("#DESCRIPTION"):
                                    marker_name = lines[i+1].strip().replace("#DESCRIPTION", "").strip()
                                    display_marker = f"[{marker_name}]"
                                    channel_list.append(display_marker)
                                    self.channel_refs[display_marker] = line
                                    i += 2
                                    continue
                                i += 1
                                continue
                            
                            sid = parts[3]
                            tsid = parts[4]
                            onid = parts[5]
                            satfreq = parts[6].lower()
                            satfreq = f"00{satfreq}" if len(satfreq) == 6 else satfreq.zfill(8)

                            search_keys = [
                                f"{int(sid, 16):04x}:{satfreq}:{int(tsid, 16):04x}:{int(onid, 16):04x}",
                                f"{sid.lower()}:{satfreq}:{tsid.lower()}:{onid.lower()}"
                            ]

                            channel_name = None
                            for search_key in search_keys:
                                channel_name = lamedb_services.get(search_key)
                                if channel_name:
                                    break

                            if not channel_name:
                                channel_name = f"Unknown ({search_keys[0]})"

                            channel_list.append(channel_name)
                            self.channel_refs[channel_name] = line
                        i += 1
                        
                elif line.startswith("#DESCRIPTION"):
                    marker_name = line.replace("#DESCRIPTION", "").strip()
                    display_marker = f"[{marker_name}]"
                    if display_marker not in channel_list:
                        channel_list.append(display_marker)
                        self.channel_refs[display_marker] = "#SERVICE 1:64:0:0:0:0:0:0:0:0:"
                    i += 1
                else:
                    i += 1

            self["channel_list"].setList(channel_list)
        except Exception as e:
            log_debug(f"Error loading bouquet channels: {str(e)}")

    def load_satellite_names(self):
        sat_list = []
        paths = ["/etc/tuxbox/satellites.xml", "/etc/enigma2/satellites.xml"]
        xml_path = None
        for path in paths:
            if os.path.exists(path):
                xml_path = path
                break
        if not xml_path:
            return sat_list
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for sat in root.findall('sat'):
                name = sat.get('name', '')
                position_raw = sat.get('position', '')
                if name and position_raw:
                    pos_val = int(position_raw)
                    if pos_val < 0:
                        deg = abs(pos_val) / 10.0
                        pos_str = f"{deg:.1f}°W".replace(".0°W", "°W")
                    else:
                        if pos_val > 1800:
                            deg = (3600 - pos_val) / 10.0
                            pos_str = f"{deg:.1f}°W".replace(".0°W", "°W")
                        else:
                            deg = pos_val / 10.0
                            pos_str = f"{deg:.1f}°E".replace(".0°E", "°E")

                    clean_name = re.sub(r'\(\d+\)\s*', '', name)
                    display_name = f"{clean_name} ({pos_str})"
                    sat_list.append((display_name, pos_str)) # POPRAVLJENO: pos_str umesto lamedb_pos
        except Exception as e:
            log_debug(f"Error parsing satellites.xml: {str(e)}")
        return sat_list

    def satellite_filter(self):
        xml_satellites = self.load_satellite_names()
        existing_sats_in_db = set(service['satellite'] for service in self.all_services if service.get('satellite'))

        choices = [("All Satellite", "All Satellite"), ("Terrestrial", "Terrestrial")]
        for display_name, lamedb_pos in xml_satellites:
            if lamedb_pos in existing_sats_in_db:
                choices.append((display_name, lamedb_pos))

        if "Unknown" in existing_sats_in_db:
            choices.append(("Unknown Satellites", "Unknown"))

        self.session.openWithCallback(
            self.satellite_selected,
            ChoiceBox,
            title="Select Satellite",
            list=choices
        )

    def satellite_selected(self, choice):
        if choice and len(choice) > 1:
            self.current_satellite = choice[1]
            self.filter_mode = "All"
            self.apply_filters()
            self["status"].setText(f"Filter: {self.current_satellite}")

    def load_all_bouquets(self):
        self.bouquet_names = {}
        self.bouquet_files = {}
        bouquets_file = "/etc/enigma2/bouquets.tv"
        if not os.path.exists(bouquets_file):
            return
        
        bouquet_order = []
        try:
            with open(bouquets_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if "FROM BOUQUET" in line:
                        start = line.find('"') + 1
                        end = line.find('"', start)
                        if start != -1 and end != -1:
                            bouquet_order.append(line[start:end])
        except:
            return
        
        bouquet_display_list = []
        for bouquet_file in bouquet_order:
            file_path = os.path.join("/etc/enigma2", bouquet_file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith("#NAME"):
                            display_name = first_line.replace("#NAME", "", 1).strip()
                            self.bouquet_names[display_name] = bouquet_file
                            self.bouquet_files[bouquet_file] = display_name
                            bouquet_display_list.append(display_name)
                except:
                    pass
        self["bouquet_list"].setList(bouquet_display_list)

    def bouquet_filter(self):
        if not self.bouquet_names:
            return
        choices = [(name, file) for name, file in self.bouquet_names.items()]
        self.session.openWithCallback(self.bouquet_selected, ChoiceBox, title="Select Bouquet", list=choices)

    def bouquet_selected(self, choice):
        if choice and choice[1]:
            bouquet_file = choice[1]
            for name, file in self.bouquet_names.items():
                if file == bouquet_file:
                    self.current_bouquet = name
                    self.current_bouquet_file = file
                    self.load_bouquet_channels(file)
                    self["status"].setText(f"Loaded bouquet: {name}")
                    break

    def open_move_editor(self):
        choices = [
            ("Ciefp Settings Downloader (GitHub liste)", "settings_downloader"),
            ("Ciefp Satellites.xml Editor (Edit Transponders)", "satellites_editor"),
            ("Ciefp Whitelist Streamrelay (Generate Whitelist)", "whitelist_streamrelay"),
            ("Ciefp Settings Motor (Download Motor Settings)", "settings_motor"),
            ("Ciefp Channel Editor (Move/Delete)", "channel_editor"),
            ("Ciefp Bouquet Editor (Move/Delete Bouquets)", "bouquet_editor"),
            ("Ciefp Channel Manager (Copy/Install)", "channel_manager"),
            ("Ciefp Select Satellite (Select Satellite)", "satellite_selector"),
            ("Ciefp CAID Manager", "caid_manager"),
            ("Ciefp Settings Comparison (Diff GitHub vs Local)", "comparison"),
            ("Ciefp Signal Info (Signal / SNR / AGC)", "signal_info"),   # ← NOVO
        ]
        self.session.openWithCallback(self.main_menu_selected, ChoiceBox,
                                      title="Ciefp E2 Editor - Main Menu",
                                      list=choices)

    # U metodi main_menu_selected, dodajte novi case:
    def main_menu_selected(self, choice):
        if not choice or len(choice) < 2:
            return
        action = choice[1]

        if action == "divider":
            return

        if action == "settings_downloader":
            self.session.open(CiefpSettingsDownloaderScreen)
        elif action == "satellites_editor":
            self.session.open(CiefpSatelliteXmlReader)
        elif action == "whitelist_streamrelay":
            self.session.open(WhitelistScreen)
        elif action == "settings_motor":
            self.session.open(CiefpSettingsScreen)
        elif action == "channel_editor":
            if self.current_bouquet_file:
                self.session.open(CiefpChannelEditor, self.current_bouquet_file)
        elif action == "bouquet_editor":
            self.session.open(CiefpBouquetEditor)
        elif action == "channel_manager":
            self.session.open(CiefpChannelManager)
        elif action == "satellite_selector":
            self.session.open(CiefpSelectSatellite)
        elif action == "caid_manager":
            self.session.open(CiefpCAIDManager)
        elif action == "comparison":
            from .plugin_comparison import CiefpComparisonScreen
            self.session.open(CiefpComparisonScreen)
        elif action == "signal_info":
            self.session.open(CiefpSignalInfoScreen)    

    def exit(self):
        self.close()


def main(session, **kwargs):
    session.open(CiefpE2editorMain)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="{0} v{1}".format(PLUGIN_NAME, PLUGIN_VERSION),
            description="Advanced Channel and Bouquet Editor",
            icon=PLUGIN_ICON,
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]