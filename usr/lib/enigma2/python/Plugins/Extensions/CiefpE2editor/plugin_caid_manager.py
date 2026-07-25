# plugin_caid_manager.py - FIXED VERSION
from __future__ import absolute_import
from enigma import eServiceReference, iServiceInformation, eTimer
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import fileExists
import os
import re

class CiefpCAIDManager(Screen):
    """CAID Manager - prikazuje CAID-ove za kanale sa satelita i iz buketa"""
    
    skin = """
        <screen position="center,center" size="1920,1080"  backgroundColor="#011a2e">
            <widget name="separator0" position="0,5" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
            <widget name="plugin_title" position="0,10" size="1920,40" font="Bold;30" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="..:: Ciefp CAID Manager ::.." />
            <widget name="services_title" position="10,50" size="900,35" font="Bold;30" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="SERVICES - CAIDs" />
            <widget name="channels_title" position="950,50" size="950,35" font="Bold;30" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="CHANNELS - CAIDs" />
            <widget name="separator1" position="0,87" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
            <widget name="services_list" position="20,90" size="900,858" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;26" backgroundColor="#011a2e" />
            <widget name="channels_list" position="920,90" size="980,858" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;26" backgroundColor="#011a2e" />
            <widget name="status" position="10,950" size="1900,40" font="Regular;24" backgroundColor="#011a2e" foregroundColor="#00FF00" />
            <widget name="separator2" position="0,990" size="1920,3" backgroundColor="#d5fa02" zPosition="1" /> 
            <widget name="red_button" position="10,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#9F1313" foregroundColor="#FFFFFF" text="Exit" />
            <widget name="green_button" position="370,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#1F771F" foregroundColor="#FFFFFF" text="Satellite" />
            <widget name="yellow_button" position="740,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#9F9F13" foregroundColor="#000000" text="Filters Menu" />
            <widget name="blue_button" position="1110,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#1F1F77" foregroundColor="#FFFFFF" text="Bouquets" />
            <widget name="menu_button" position="1480,1000" size="350,40" font="Bold;28" halign="center" backgroundColor="#777777" foregroundColor="#FFFFFF" text="MENU" />
            <widget name="info" position="900,950" size="900,40" font="Regular;30" halign="right" foregroundColor="#00FF00" backgroundColor="#011a2e" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.closed = False

        self["services_list"] = MenuList([])
        self["channels_list"] = MenuList([])
        self["bouquet_list"] = MenuList([])

        # Separatori
        self["separator0"] = Label()
        self["separator1"] = Label()
        self["separator2"] = Label()
        self["separator3"] = Label()

        self["plugin_title"] = Label("..:: Ciefp CAID Manager ::..")
        self["services_title"] = Label("SERVICES - CAIDs")
        self["channels_title"] = Label("CHANNELS - CAIDs")
        self["status"] = Label("Loading...")
        self["info"] = Label("CAID Manager v2.0")

        self["red_button"] = Label("Exit")
        self["green_button"] = Label("Satellite")
        self["yellow_button"] = Label("Provider / CAID")
        self["blue_button"] = Label("Bouquets")
        self["menu_button"] = Label("MENU")

        # Podaci
        self.all_services = []
        self.filtered_services = []
        self.service_caids = {}
        self.service_providers = {}
        self.service_refs = {}
        self.service_active_caid = {}
        
        self.bouquet_channels = []
        self.bouquet_caids = {}
        self.bouquet_providers = {}
        self.bouquet_refs = {}
        self.bouquet_active_caid = {}
        
        self.bouquet_names = {}
        self.bouquet_files = {}
        self.current_bouquet = None
        self.current_bouquet_file = None
        
        # Filteri
        self.current_satellite = "All Satellite"
        self.filter_provider = None
        self.filter_caid = None
        self.filter_mode = "All"
        self.show_missing_only = False

        self.active_panel = 0
        self.updating = False

        self.refresh_timer = eTimer()
        self.refresh_timer.callback.append(self.safe_refresh)
        self.refresh_timer.start(2000, False)

        self.message_timer = eTimer()
        self.message_timer.callback.append(self.show_delayed_message)

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
                "yellow": self.provider_caid_filter,
                "blue": self.bouquet_filter,
                "menu": self.open_main_menu,
            },
            -1
        )

        self.onLayoutFinish.append(self.init_data)

    def get_active_bouquet_from_enigma(self):
        """Dohvata trenutno aktivni SATELITSKI buket iz Enigme2 sistema (preskače tematske)"""
        try:
            from enigma import eServiceCenter, eServiceReference

            # Dohvati trenutni service reference
            service_ref = self.session.nav.getCurrentlyPlayingServiceReference()
            if not service_ref:
                print("[CAID DEBUG] Nema aktivnog servisa")
                return None

            # Dohvati listu svih buketa
            bouquet_root = eServiceReference('1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet')
            service_handler = eServiceCenter.getInstance()
            list_of_bouquets = service_handler.list(bouquet_root)

            if list_of_bouquets is None:
                print("[CAID DEBUG] Nema buketa")
                return None

            # Tražimo SATELITSKI buket koji sadrži trenutni kanal
            while True:
                bouquet = list_of_bouquets.getNext()
                if not bouquet.valid():
                    break

                bouquet_name = service_handler.info(bouquet).getName(bouquet)

                # PRESKAČI TEMATSKE BUKETE (počinju sa ##)
                if self.is_thematic_bouquet(bouquet_name):
                    print(f"[CAID DEBUG] Preskačem tematski buket: {bouquet_name}")
                    continue

                # Otvorimo buket i provjerimo da li sadrži trenutni kanal
                bouquet_content = service_handler.list(bouquet)
                if bouquet_content:
                    while True:
                        service = bouquet_content.getNext()
                        if not service.valid():
                            break
                        if service_ref.toString() == service.toString():
                            # Pronađen SATELITSKI buket koji sadrži trenutni kanal
                            print(f"[CAID DEBUG] Pronađen satelitski buket: {bouquet_name}")
                            return bouquet_name

            print("[CAID DEBUG] Nije pronađen satelitski buket za aktivni kanal")
            return None
        except Exception as e:
            print(f"[CAID DEBUG] Greška pri dohvatanju aktivnog buketa: {str(e)}")
            return None

    def is_thematic_bouquet(self, bouquet_name):
        """Provjerava da li je buket tematski (počinje sa ##)"""
        if not bouquet_name:
            return True  # Ako nema imena, smatraj ga tematskim

        # Tematski buketi počinju sa ##
        if bouquet_name.strip().startswith("##"):
            return True

        # Dodatna provjera: ako ime sadrži samo ## bez satelitske oznake
        if "##" in bouquet_name and not any(c in bouquet_name for c in ['E', 'W', '°']):
            return True

        return False

    def get_satellite_bouquets(self):
        """Dohvata listu samo satelitskih buketa (ne tematskih)"""
        sat_bouquets = {}
        for name, file in self.bouquet_names.items():
            if not self.is_thematic_bouquet(name):
                sat_bouquets[name] = file
        return sat_bouquets

    def get_last_used_bouquet(self):
        """Dohvata posljednji korišteni buket iz cache-a"""
        cache_file = "/tmp/caid_manager_last_bouquet.txt"
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return f.read().strip()
        except:
            pass
        return None

    def save_last_used_bouquet(self, bouquet_name):
        """Čuva posljednji korišteni buket u cache"""
        cache_file = "/tmp/caid_manager_last_bouquet.txt"
        try:
            with open(cache_file, 'w') as f:
                f.write(bouquet_name)
        except:
            pass

    def get_reference_from_enigma_system(self, channel_name):
        """Dohvata zvaničnu Enigma2 referencu direktno iz memorije risivera"""
        print("[ENIGMA] Searching:", channel_name)
        try:
            from enigma import eServiceCenter, eServiceReference
            # KORIGOVANO: Koristimo ispravan query string umesto 'All'
            all_services_ref = eServiceReference('1:7:1:0:0:0:0:0:0:0:FROM PROVIDERS All Services TV')
            service_handler = eServiceCenter.getInstance()
            list_of_services = service_handler.list(all_services_ref)
            if list_of_services is None:
                print("[ENIGMA] list_of_services == None")
                return None

            if list_of_services is not None:
                while True:
                    service = list_of_services.getNext()
                    if not service.valid():
                        break
                    info = service_handler.info(service)
                    name_in_system = info.getName(service)

                    if name_in_system.strip().lower() == channel_name.strip().lower():
                        raw_ref = service.toString()
                        parts = raw_ref.split(':')
                        if len(parts) >= 7:
                            for i in range(3, 7):
                                parts[i] = parts[i].upper()
                            return ":".join(parts)
                        return raw_ref.upper()
        except Exception as e:
            # Ignorišemo greške, samo nastavljamo dalje
            pass
        return None

    def safe_refresh(self):
        if not self.closed and not self.updating:
            try:
                self.refresh_active_caids()
            except:
                pass

    def show_delayed_message(self):
        self.message_timer.stop()
        if not self.closed and hasattr(self, '_pending_message'):
            try:
                msg, msg_type, timeout = self._pending_message
                self.session.open(MessageBox, msg, msg_type, timeout=timeout)
            except:
                pass
            finally:
                if hasattr(self, '_pending_message'):
                    del self._pending_message

    def safe_open_message(self, message, msg_type=MessageBox.TYPE_INFO, timeout=3):
        if not self.closed:
            self._pending_message = (message, msg_type, timeout)
            self.message_timer.start(100, True)

    def safe_open_message_with_callback(self, message, msg_type, callback):
        if not self.closed:
            self.session.openWithCallback(callback, MessageBox, message, msg_type)

    def update_panel_focus(self):
        if self.closed:
            return
        try:
            if self.active_panel == 0:
                self["status"].setText("Focus: SERVICES panel | OK for Options")
            else:
                self["status"].setText("Focus: CHANNELS panel | OK for Options")
        except:
            pass

    def move_left(self):
        if self.closed:
            return
        if self.active_panel > 0:
            self.active_panel -= 1
            self.update_panel_focus()

    def move_right(self):
        if self.closed:
            return
        if self.active_panel < 1:
            self.active_panel += 1
            self.update_panel_focus()

    def move_up(self):
        if self.closed:
            return
        try:
            if self.active_panel == 0:
                self["services_list"].up()
            else:
                self["channels_list"].up()
        except:
            pass

    def move_down(self):
        if self.closed:
            return
        try:
            if self.active_panel == 0:
                self["services_list"].down()
            else:
                self["channels_list"].down()
        except:
            pass

    def ok_pressed(self):
        if self.closed:
            return

        if self.active_panel == 0:
            current = self.get_current_service()
            if not current:
                return

            channel_name = self.extract_clean_channel_name(current)
            options = [
                ("Copy Selected to Active Bouquet", "copy"),
                ("Copy ALL Filtered to Active Bouquet", "copy_all_filtered"),
                ("Delete from Service List", "delete"),
                ("Show CAIDs for this channel", "show_caids")
            ]

            self.session.openWithCallback(
                self.services_callback,
                ChoiceBox,
                title=f"Options for: {channel_name}",
                list=options
            )

        else:
            current = self.get_current_channel()
            if not current:
                return
            
            channel_name = self.extract_clean_channel_name(current)
            options = [
                ("Remove from Bouquet", "remove_from_bouquet"),
                ("Show CAIDs for this channel", "show_caids")
            ]
            
            self.session.openWithCallback(
                self.channels_callback,
                ChoiceBox,
                title=f"Options for: {channel_name}",
                list=options
            )

    def get_current_service(self):
        try:
            if hasattr(self["services_list"], 'getCurrent'):
                current = self["services_list"].getCurrent()
                if current:
                    return current
        except:
            pass
        return None

    def get_current_channel(self):
        try:
            if hasattr(self["channels_list"], 'getCurrent'):
                current = self["channels_list"].getCurrent()
                if current:
                    return current
        except:
            pass
        return None

    def extract_clean_channel_name(self, display_text):
        if not display_text:
            return ""
        
        text = display_text.replace(" (IPTV)", "").replace(" (StreamRelay)", "")
        
        if " - " in text:
            parts = text.split(" - ")
            if parts[1] == "FTA" or "(Active)" in parts[1] or re.match(r'^[0-9A-Fa-f]{4}$', parts[1].strip()):
                return parts[0].strip()
        
        if text.startswith("[") and text.endswith("]"):
            return text[1:-1]
        
        return text.strip()

    def services_callback(self, answer):
        if self.closed or not answer:
            return
        action = answer[1]

        if action == "copy":
            self.copy_service_to_bouquet()
        elif action == "copy_all_filtered":
            self.copy_all_filtered_to_bouquet()
        elif action == "delete":
            self.delete_selected_service()
        elif action == "show_caids":
            self.show_channel_caids(0)

    def channels_callback(self, answer):
        if self.closed or not answer:
            return
        action = answer[1]
        
        if action == "remove_from_bouquet":
            self.remove_from_bouquet()
        elif action == "show_caids":
            self.show_channel_caids(1)

    def get_service_type_from_lamedb(self, channel_name):
        """Dohvata tačan tip servisa iz lamedb-a za dati kanal"""
        try:
            lamedb_path = "/etc/enigma2/lamedb"
            if not os.path.exists(lamedb_path):
                print(f"[CAID DEBUG] lamedb nije pronađen: {lamedb_path}")
                return "1"

            with open(lamedb_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # Tražimo kanal u lamedb-u
            for i, line in enumerate(lines):
                line = line.strip()
                # Preskoči p: i c: linije
                if line.startswith("p:") or line.startswith("c:"):
                    continue

                if ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 5:
                        # Proveri da li je sledeća linija ime kanala
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            # Ako sledeća linija nije p: ili c: i odgovara imenu kanala
                            if next_line == channel_name:
                                # parts[0]=sid, parts[1]=namespace, parts[2]=tsid, parts[3]=onid, parts[4]=srv_type
                                srv_type = parts[4].strip()
                                print(f"[CAID DEBUG] Pronađen tip za '{channel_name}': {srv_type}")
                                return srv_type
            print(f"[CAID DEBUG] Tip za '{channel_name}' nije pronađen, vraćam '1'")
            return "1"
        except Exception as e:
            print(f"[CAID DEBUG] Greška u get_service_type_from_lamedb: {str(e)}")
            return "1"

    def convert_service_type_to_hex(self, srv_type_dec):
        """Konvertuje decimalni tip servisa iz lamedb u heksadecimalni za Enigma2 referencu"""
        try:
            # Ako je već hex (sadrži slova), vrati kako je
            if any(c in srv_type_dec.upper() for c in 'ABCDEF'):
                return srv_type_dec.upper()
            # Konvertuj decimal u hex
            dec_val = int(srv_type_dec)
            hex_val = f"{dec_val:X}"
            return hex_val
        except:
            return srv_type_dec

    def copy_service_to_bouquet(self):
        if self.closed:
            return

        current = self.get_current_service()
        if not current:
            print("[CAID DEBUG] Kopiranje prekinuto: Nije selektovan nijedan kanal sa leve strane.")
            return

        channel_name = self.extract_clean_channel_name(current)
        print(f"\n[CAID DEBUG] === ZAPOČETO KOPIRANJE KANALA: '{channel_name}' ===")

        if not self.current_bouquet_file:
            print("[CAID DEBUG] Greška: Aktivni buket fajl nije definisan.")
            self.safe_open_message("Please open a bouquet first via the Blue button.", MessageBox.TYPE_ERROR)
            return

        existing_names = [self.extract_clean_channel_name(item) for item in self.bouquet_channels]
        if channel_name in existing_names:
            print(f"[CAID DEBUG] Kanal '{channel_name}' već postoji u aktivnom buketu.")
            self["status"].setText(f"Channel '{channel_name}' already exists in bouquet!")
            return

        service_ref = None
        service_caids = []
        service_provider = "Unknown"

        # 1. Prvo pokušaj dohvatiti direktno iz Enigme (sistemska referenca) - ONEMOGUĆENO
        # if hasattr(self, 'get_reference_from_enigma_system'):
        #     sistemska_ref = self.get_reference_from_enigma_system(channel_name)
        #     if sistemska_ref:
        #         service_ref = sistemska_ref
        #         service_caids = self.service_caids.get(channel_name, [])
        #         service_provider = self.service_providers.get(channel_name, "Unknown")
        #         print(f"[CAID DEBUG] Pronađena ZVANIČNA sistemska referenca: {service_ref}")

        # 2. Tražim u all_services
        if not service_ref:
            for service in self.all_services:
                if service['name'] == channel_name:
                    if "FROM" not in service['ref'].upper():
                        service_ref = service['ref']
                        service_caids = self.service_caids.get(channel_name, [])
                        service_provider = self.service_providers.get(channel_name, "Unknown")
                        print(f"[CAID DEBUG] Pronađena referenca u all_services: {service_ref}")
                        break

        # 3. Tražim u service_refs alternativno
        if not service_ref:
            for ref, name in self.service_refs.items():
                if name == channel_name:
                    if "FROM" not in ref.upper():
                        service_ref = ref
                        service_caids = self.service_caids.get(channel_name, [])
                        service_provider = self.service_providers.get(channel_name, "Unknown")
                        print(f"[CAID DEBUG] Pronađena referenca u service_refs: {service_ref}")
                        break

        if service_ref:
            # Ako referenca iz lamedb-a nema tip na početku, moramo da napravimo punu Enigma2 referencu!
            if not service_ref.startswith("1:") and not service_ref.startswith("#SERVICE"):
                parts = service_ref.split(":")
                if len(parts) >= 4:
                    sid = f"{int(parts[0], 16):X}"
                    tsid = f"{int(parts[2], 16):X}"
                    onid = f"{int(parts[3], 16):X}"

                    raw_ns = parts[1].upper()
                    if len(raw_ns) > 4 and raw_ns.endswith("0000"):
                        ns_val = int(raw_ns, 16)
                        ns = f"{ns_val:X}"
                    else:
                        ns = raw_ns.lstrip('0') or '0'

                    # DOHVATI TIP SERVISA IZ LAMEDB
                    srv_type_raw = self.get_service_type_from_lamedb(channel_name)
                    print(
                        f"[CAID DEBUG] get_service_type_from_lamedb vratio: '{srv_type_raw}' za kanal '{channel_name}'")

                    # KONVERTUJ DECIMAL U HEX (22 -> 16, 25 -> 19, 1 -> 1, itd.)
                    srv_type = self.convert_service_type_to_hex(srv_type_raw)
                    print(f"[CAID DEBUG] Nakon konverzije: '{srv_type_raw}' -> '{srv_type}'")

                    constructed_ref = f"1:0:{srv_type}:{sid}:{tsid}:{onid}:{ns}:0:0:0:"
                    print(
                        f"[CAID DEBUG] Konvertujem sirovu lamedb referencu u ISPRAVAN Enigma2 format: {constructed_ref}")
                    service_line = f"#SERVICE {constructed_ref}"
                else:
                    service_line = f"#SERVICE {service_ref}"
            else:
                if not service_ref.startswith("#SERVICE"):
                    # Popravi tip ako je pogrešan
                    if service_ref.startswith("1:0:1:"):
                        srv_type_raw = self.get_service_type_from_lamedb(channel_name)
                        srv_type = self.convert_service_type_to_hex(srv_type_raw)
                        if srv_type != "1":
                            service_ref = service_ref.replace("1:0:1:", f"1:0:{srv_type}:")
                    service_line = f"#SERVICE {service_ref}"
                else:
                    service_line = service_ref

            print(f"[CAID DEBUG] Konačna linija za upis u buket fajl: {service_line}")

            active_caid = self.get_active_caid_from_ecm()
            display = self.format_channel_display(channel_name, service_caids, active_caid)

            self.updating = True
            try:
                self.bouquet_channels.append(display)
                self.bouquet_refs[channel_name] = service_line
                self.bouquet_caids[channel_name] = service_caids
                self.bouquet_providers[channel_name] = service_provider
                if active_caid and active_caid in service_caids:
                    self.bouquet_active_caid[channel_name] = active_caid

                self["channels_list"].setList(self.bouquet_channels)

                print(f"[CAID DEBUG] Pozivam automatsko čuvanje u fajl: {self.current_bouquet_file}")
                save_result = self._auto_save_bouquet()
                print(f"[CAID DEBUG] Ishod čuvanja: {save_result}")

                self.apply_filters()
                self["status"].setText(f"Copied '{channel_name}' to active bouquet.")
            except Exception as e:
                print(f"[CAID DEBUG] Izuzetak tokom upisa/kopiranja: {str(e)}")
            finally:
                self.updating = False
        else:
            print(f"[CAID DEBUG] EROR: Uopšte nije pronađena referenca za kanal '{channel_name}'!")
            self.safe_open_message(f"Could not find reference for '{channel_name}'!", MessageBox.TYPE_ERROR)
        print("[CAID DEBUG] === KRAJ PROCESA KOPIRANJA ===\n")

    def copy_all_filtered_to_bouquet(self):
        if self.closed:
            return

        if not self.current_bouquet_file:
            self.safe_open_message("Please open a bouquet first via the Blue button.", MessageBox.TYPE_ERROR)
            return

        if not self.filtered_services:
            self["status"].setText("No filtered channels to copy!")
            return

        print(f"\n[CAID DEBUG] === ZAPOČETO MASOVNO KOPIRANJE ({len(self.filtered_services)} kanala) ===")

        existing_names = [self.extract_clean_channel_name(item) for item in self.bouquet_channels]
        copied_count = 0
        skipped_count = 0

        self.updating = True
        try:
            for display_item in self.filtered_services:
                channel_name = self.extract_clean_channel_name(display_item)

                if channel_name in existing_names:
                    skipped_count += 1
                    continue

                service_ref = None
                service_caids = []
                service_provider = "Unknown"

                # Tražim u all_services
                for service in self.all_services:
                    if service['name'] == channel_name:
                        if "FROM" not in service['ref'].upper():
                            service_ref = service['ref']
                            service_caids = self.service_caids.get(channel_name, [])
                            service_provider = self.service_providers.get(channel_name, "Unknown")
                            print(f"[CAID DEBUG] Pronađena referenca u all_services: {service_ref}")
                            break

                # Tražim u service_refs alternativno
                if not service_ref:
                    for ref, name in self.service_refs.items():
                        if name == channel_name:
                            if "FROM" not in ref.upper():
                                service_ref = ref
                                service_caids = self.service_caids.get(channel_name, [])
                                service_provider = self.service_providers.get(channel_name, "Unknown")
                                print(f"[CAID DEBUG] Pronađena referenca u service_refs: {service_ref}")
                                break

                if service_ref:
                    if not service_ref.startswith("1:") and not service_ref.startswith("#SERVICE"):
                        parts = service_ref.split(":")
                        if len(parts) >= 4:
                            # SID - konvertujemo iz hex u hex (samo velika slova)
                            sid = f"{int(parts[0], 16):X}"
                            tsid = f"{int(parts[2], 16):X}"
                            onid = f"{int(parts[3], 16):X}"

                            raw_ns = parts[1].upper()
                            if len(raw_ns) > 4 and raw_ns.endswith("0000"):
                                ns_val = int(raw_ns, 16)
                                ns = f"{ns_val:X}"
                            else:
                                ns = raw_ns.lstrip('0') or '0'

                            # DOHVATI TIP SERVISA IZ LAMEDB (OVO JE BITNO!)
                            srv_type_raw = self.get_service_type_from_lamedb(channel_name)
                            print(
                                f"[CAID DEBUG] get_service_type_from_lamedb vratio: '{srv_type_raw}' za kanal '{channel_name}'")

                            # KONVERTUJ TIP IZ DECIMAL U HEX (22->16, 25->19, 1->1)
                            srv_type = self.convert_service_type_to_hex(srv_type_raw)
                            print(f"[CAID DEBUG] Nakon konverzije tipa: '{srv_type_raw}' -> '{srv_type}'")

                            constructed_ref = f"1:0:{srv_type}:{sid}:{tsid}:{onid}:{ns}:0:0:0:"
                            print(
                                f"[CAID DEBUG] Konvertujem sirovu lamedb referencu u ISPRAVAN Enigma2 format: {constructed_ref}")
                            service_line = f"#SERVICE {constructed_ref}"
                        else:
                            service_line = f"#SERVICE {service_ref}"
                    else:
                        if not service_ref.startswith("#SERVICE"):
                            # Popravi tip ako je pogrešan
                            srv_type_raw = self.get_service_type_from_lamedb(channel_name)
                            srv_type = self.convert_service_type_to_hex(srv_type_raw)
                            parts = service_ref.split(":")
                            if len(parts) >= 3:
                                parts[2] = srv_type
                                service_ref = ":".join(parts)
                            service_line = f"#SERVICE {service_ref}"
                        else:
                            service_line = service_ref

                    print(f"[CAID DEBUG] Konačna linija za upis: {service_line}")

                    active_caid = self.get_active_caid_from_ecm()
                    display = self.format_channel_display(channel_name, service_caids, active_caid)

                    self.bouquet_channels.append(display)
                    self.bouquet_refs[channel_name] = service_line
                    self.bouquet_caids[channel_name] = service_caids
                    self.bouquet_providers[channel_name] = service_provider
                    if active_caid and active_caid in service_caids:
                        self.bouquet_active_caid[channel_name] = active_caid

                    existing_names.append(channel_name)
                    copied_count += 1

            if copied_count > 0:
                self["channels_list"].setList(self.bouquet_channels)
                self._auto_save_bouquet()
                self.apply_filters()
                self.safe_open_message(
                    f"Successfully copied {copied_count} channels!\n(Skipped {skipped_count} duplicates)",
                    MessageBox.TYPE_INFO, timeout=5)
                self["status"].setText(f"Copied {copied_count} channels to active bouquet.")
            else:
                self.safe_open_message(
                    f"No new channels copied. All {skipped_count} channels already exist in bouquet.",
                    MessageBox.TYPE_INFO, timeout=5)
                self["status"].setText("Bulk copy skipped: All channels already exist.")

        except Exception as e:
            print(f"[CAID DEBUG] Izuzetak tokom masovnog kopiranja: {str(e)}")
            self.safe_open_message(f"Error during bulk copy: {str(e)}", MessageBox.TYPE_ERROR)
        finally:
            self.updating = False
            print("[CAID DEBUG] === KRAJ MASOVNOG KOPIRANJA ===\n")

    def delete_selected_service(self):
        if self.closed:
            return
            
        current = self.get_current_service()
        if not current:
            return

        channel_name = self.extract_clean_channel_name(current)

        self.safe_open_message_with_callback(
            f"Are you sure you want to delete '{channel_name}' from the service list?",
            MessageBox.TYPE_YESNO,
            lambda confirmed: self._confirm_delete_service(confirmed, channel_name)
        )

    def _confirm_delete_service(self, confirmed, channel_name):
        if not confirmed or self.closed:
            return

        try:
            current_list = self["services_list"].list
            item_to_remove = None
            for item in current_list:
                if self.extract_clean_channel_name(item) == channel_name:
                    item_to_remove = item
                    break
            
            if item_to_remove and item_to_remove in current_list:
                self.updating = True
                
                try:
                    current_list.remove(item_to_remove)
                    self["services_list"].setList(current_list)
                    
                    self.all_services = [s for s in self.all_services if s['name'] != channel_name]
                    self.service_caids.pop(channel_name, None)
                    self.service_providers.pop(channel_name, None)
                    self.service_active_caid.pop(channel_name, None)
                    self.service_refs = {ref: name for ref, name in self.service_refs.items() if name != channel_name}
                    
                    if channel_name in self.bouquet_refs:
                        self._remove_channel_from_bouquet(channel_name)
                    
                    self.apply_filters()
                    
                    self["status"].setText(f"Deleted '{channel_name}' from view.")
                finally:
                    self.updating = False
            else:
                self["status"].setText(f"Could not find '{channel_name}' in list.")
        except Exception as e:
            self["status"].setText(f"Error deleting: {str(e)}")
            self.updating = False

    def _remove_channel_from_bouquet(self, channel_name):
        try:
            item_to_remove = None
            for item in self.bouquet_channels:
                if self.extract_clean_channel_name(item) == channel_name:
                    item_to_remove = item
                    break
            
            if item_to_remove and item_to_remove in self.bouquet_channels:
                self.bouquet_channels.remove(item_to_remove)
                self.bouquet_refs.pop(channel_name, None)
                self.bouquet_caids.pop(channel_name, None)
                self.bouquet_providers.pop(channel_name, None)
                self.bouquet_active_caid.pop(channel_name, None)
                self["channels_list"].setList(self.bouquet_channels)
                self._auto_save_bouquet()
        except:
            pass

    def remove_from_bouquet(self):
        if self.closed:
            return
            
        current = self.get_current_channel()
        if not current:
            return

        channel_name = self.extract_clean_channel_name(current)

        self.safe_open_message_with_callback(
            f"Are you sure you want to remove '{channel_name}' from bouquet?",
            MessageBox.TYPE_YESNO,
            lambda confirmed: self._confirm_remove_from_bouquet(confirmed, channel_name)
        )

    def _confirm_remove_from_bouquet(self, confirmed, channel_name):
        if not confirmed or self.closed:
            return

        try:
            current_list = self["channels_list"].list
            item_to_remove = None
            for item in current_list:
                if self.extract_clean_channel_name(item) == channel_name:
                    item_to_remove = item
                    break
            
            if item_to_remove and item_to_remove in current_list:
                self.updating = True
                
                try:
                    current_list.remove(item_to_remove)
                    self["channels_list"].setList(current_list)
                    
                    self.bouquet_refs.pop(channel_name, None)
                    self.bouquet_caids.pop(channel_name, None)
                    self.bouquet_providers.pop(channel_name, None)
                    self.bouquet_active_caid.pop(channel_name, None)
                    self.bouquet_channels = current_list
                    
                    self._auto_save_bouquet()
                    
                    self["status"].setText(f"Removed '{channel_name}' from bouquet and saved.")
                finally:
                    self.updating = False
            else:
                self["status"].setText(f"Could not find '{channel_name}' in bouquet.")
        except Exception as e:
            self["status"].setText(f"Error removing: {str(e)}")
            self.updating = False

    def get_active_caid_from_ecm(self):
        ecm_path = "/tmp/ecm.info"
        active_caid = None
        
        if os.path.exists(ecm_path):
            try:
                with open(ecm_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if ":" not in line:
                            continue
                        key, value = line.split(":", 1)
                        if key.strip().lower() == "caid":
                            clean_caid = value.replace("0x", "").upper().strip()
                            if len(clean_caid) < 4:
                                clean_caid = clean_caid.zfill(4)
                            active_caid = clean_caid
                            break
            except:
                pass
        return active_caid

    def refresh_active_caids(self):
        if self.closed or self.updating:
            return
            
        active_caid = self.get_active_caid_from_ecm()
        
        if active_caid:
            for name in self.service_caids:
                caids = self.service_caids.get(name, [])
                if active_caid in caids:
                    self.service_active_caid[name] = active_caid
                else:
                    self.service_active_caid[name] = None
            
            for name in self.bouquet_caids:
                caids = self.bouquet_caids.get(name, [])
                if active_caid in caids:
                    self.bouquet_active_caid[name] = active_caid
                else:
                    self.bouquet_active_caid[name] = None
            
            self.refresh_display()

    def refresh_display(self):
        if self.closed or self.updating:
            return
        
        try:
            current_service = self.get_current_service()
            current_channel = self.get_current_channel()
            
            self.apply_filters()
            if self.current_bouquet_file:
                self.load_bouquet_channels(self.current_bouquet_file)
            
            if current_service:
                try:
                    self["services_list"].setSelection(current_service)
                except:
                    pass
            if current_channel:
                try:
                    self["channels_list"].setSelection(current_channel)
                except:
                    pass
        except:
            pass

    def format_channel_display(self, name, caids, active_caid=None):
        if not caids:
            return f"{name} - FTA"
        
        if not active_caid and name in self.service_active_caid:
            active_caid = self.service_active_caid.get(name)
        
        if active_caid and active_caid in caids:
            return f"{name} - {active_caid} (Active)"
        
        return f"{name}"

    def init_data(self):
        if self.closed:
            return

        self["status"].setText("Loading data...")
        self.load_all_services()
        self.load_all_bouquets()

        # Dobij samo satelitske bukete za automatsko učitavanje
        sat_bouquets = self.get_satellite_bouquets()

        if not sat_bouquets:
            # Ako nema satelitskih buketa, koristi sve bukete
            sat_bouquets = self.bouquet_names
            self["status"].setText("No satellite bouquets found, using all bouquets...")

        # Pokušaj prvo učitati aktivni SATELITSKI buket
        active_bouquet = self.get_active_bouquet_from_enigma()
        if active_bouquet and active_bouquet in sat_bouquets:
            bouquet_file = sat_bouquets[active_bouquet]
            self.current_bouquet = active_bouquet
            self.current_bouquet_file = bouquet_file
            self.load_bouquet_channels(bouquet_file)
            self["status"].setText(f"Loaded active satellite bouquet: {active_bouquet}")
        else:
            # Ako nema aktivnog satelitskog buketa, pokušaj sa zadnjim korištenim
            last_bouquet = self.get_last_used_bouquet()
            if last_bouquet and last_bouquet in sat_bouquets:
                bouquet_file = sat_bouquets[last_bouquet]
                self.current_bouquet = last_bouquet
                self.current_bouquet_file = bouquet_file
                self.load_bouquet_channels(bouquet_file)
                self["status"].setText(f"Loaded last satellite bouquet: {last_bouquet}")
            else:
                # Ako ništa ne radi, učitaj prvi SATELITSKI buket
                if sat_bouquets:
                    first_bouquet = list(sat_bouquets.keys())[0]
                    self.current_bouquet = first_bouquet
                    self.current_bouquet_file = sat_bouquets[first_bouquet]
                    self.load_bouquet_channels(self.current_bouquet_file)
                    self["status"].setText(f"Loaded first satellite bouquet: {first_bouquet}")
                else:
                    # Ako nema satelitskih buketa, probaj sa bilo kojim
                    if self.bouquet_names:
                        first_bouquet = list(self.bouquet_names.keys())[0]
                        self.current_bouquet = first_bouquet
                        self.current_bouquet_file = self.bouquet_names[first_bouquet]
                        self.load_bouquet_channels(self.current_bouquet_file)
                        self["status"].setText(f"Loaded first bouquet: {first_bouquet}")

        self.update_panel_focus()
        self.refresh_active_caids()

    def load_all_services(self):
        if self.closed:
            return
            
        self.all_services = []
        self.service_caids = {}
        self.service_providers = {}
        self.service_refs = {}
        self.service_active_caid = {}

        lamedb_services, service_metadata = self.parse_lamedb_with_caids()
        seen_names = set()
        
        print(f"[CAID DEBUG] Parser lamedb-a vratio {len(lamedb_services)} servisa.")
        
        for ref, name in lamedb_services.items():
            if name and not name.startswith("p:") and name not in seen_names:
                seen_names.add(name)
                self.service_refs[ref] = name
                meta = service_metadata.get(ref, {"type": "1", "provider": "Unknown", "caids": []})
                
                service_info = self.parse_service_ref(ref, name, meta["type"], meta["provider"])
                if service_info:
                    self.all_services.append(service_info)
                    self.service_caids[name] = meta.get("caids", [])
                    self.service_providers[name] = meta.get("provider", "Unknown")

        print(f"[CAID DEBUG] Uspešno mapirano {len(self.all_services)} unikatnih kanala na levoj strani.")
        self.apply_filters()

    def parse_lamedb_with_caids(self):
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
                        sid = parts[0].strip()
                        satfreq = parts[1].strip().lower()
                        tsid = parts[2].strip()
                        onid = parts[3].strip()
                        srv_type = parts[4].strip()

                        key1 = f"{sid}:{satfreq}:{tsid}:{onid}"

                        try:
                            s_sid = f"{int(sid, 16):x}"
                            s_tsid = f"{int(tsid, 16):x}"
                            s_onid = f"{int(onid, 16):x}"
                            key2 = f"{s_sid}:{satfreq}:{s_tsid}:{s_onid}"
                        except:
                            key2 = f"{sid.lstrip('0') or '0'}:{satfreq}:{tsid.lstrip('0') or '0'}:{onid.lstrip('0') or '0'}"

                        name = ""
                        if i + 1 < len(lines):
                            name = lines[i + 1].strip()

                        provider_name = "Unknown"
                        caids = []

                        if i + 2 < len(lines):
                            extra_line = lines[i + 2].strip()
                            p_match = re.search(r'p:([^,]+)', extra_line)
                            if p_match:
                                provider_name = p_match.group(1).strip()

                            caid_matches = re.findall(r'[cC]:([0-9A-Fa-f]{4})', extra_line)
                            if caid_matches:
                                caids = [c.upper() for c in caid_matches]
                            else:
                                caid_matches = re.findall(r'([0-9A-Fa-f]{4})', extra_line)
                                if caid_matches:
                                    caids = [c.upper() for c in caid_matches]

                        if name and not name.startswith("p:") and not name.startswith("c:"):
                            services[key1] = name
                            services[key2] = name

                            meta = {
                                "type": srv_type,
                                "provider": provider_name,
                                "caids": caids
                            }
                            service_metadata[key1] = meta
                            service_metadata[key2] = meta

                        i += 2
                        continue
                i += 1
        except Exception as e:
            print(f"[CAID DEBUG] Greška u lamedb parseru: {str(e)}")

        return services, service_metadata

    def parse_service_ref(self, ref, name, srv_type_code="1", provider="Unknown"):
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

                service_type = "TV"
                if srv_type_code in ["2", "10", "a", "A"]:
                    service_type = "Radio"

                return {
                    'name': name,
                    'ref': ref,
                    'sid': sid,
                    'satfreq': namespace,
                    'tsid': tsid,
                    'onid': onid,
                    'satellite': satellite,
                    'type': service_type,
                    'provider': provider
                }
        except:
            pass
        return None

    def apply_filters(self):
        if self.closed or self.updating:
            return
            
        self.filtered_services = []
        active_caid = self.get_active_caid_from_ecm()
        
        bouquet_channel_names = set()
        for item in self.bouquet_channels:
            name = self.extract_clean_channel_name(item)
            bouquet_channel_names.add(name)
        
        seen_names = set()
        
        for service in self.all_services:
            name = service['name']
            
            if name in seen_names:
                continue
            seen_names.add(name)
            
            if self.current_satellite != "All Satellite":
                if self.current_satellite == "Terrestrial" and service['satellite'] != "Terrestrial":
                    continue
                elif self.current_satellite != "Terrestrial" and self.current_satellite not in service['satellite']:
                    continue
            
            if self.filter_mode == "Provider" and self.filter_provider:
                if service['provider'] != self.filter_provider:
                    continue
            
            if self.filter_mode == "CAID" and self.filter_caid:
                caids = self.service_caids.get(name, [])
                if self.filter_caid not in caids:
                    continue
            
            if self.show_missing_only:
                if name in bouquet_channel_names:
                    continue
            
            caids = self.service_caids.get(name, [])
            display = self.format_channel_display(name, caids, active_caid)
            self.filtered_services.append(display)
        
        try:
            self["services_list"].setList(self.filtered_services)
        except:
            pass

    def satellite_filter(self):
        if self.closed:
            return
            
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
        if self.closed or not choice or len(choice) <= 1:
            return
            
        self.current_satellite = choice[1]
        self.filter_mode = "All"
        self.filter_provider = None
        self.filter_caid = None
        self.show_missing_only = False
        self.apply_filters()

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
            import xml.etree.ElementTree as ET
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
                    sat_list.append((display_name, pos_str))
        except:
            pass
        return sat_list

    def provider_caid_filter(self):
        if self.closed:
            return
            
        choices = [
            ("Filter by Provider", "provider"),
            ("Filter by CAID", "caid"),
            ("Show ONLY missing channels (not in bouquet)", "missing"),
            ("Show ALL channels", "all"),
            ("Clear Filters", "clear")
        ]
        
        self.session.openWithCallback(
            self.provider_caid_selected,
            ChoiceBox,
            title="Filter by Provider, CAID or Missing Channels",
            list=choices
        )

    def provider_caid_selected(self, choice):
        if self.closed or not choice:
            return
        
        mode = choice[1]
        
        if mode == "clear" or mode == "all":
            self.filter_mode = "All"
            self.filter_provider = None
            self.filter_caid = None
            self.show_missing_only = False
            self.apply_filters()
            return
        
        if mode == "missing":
            self.show_missing_only = True
            self.apply_filters()
            return
        
        if mode == "provider":
            self.open_provider_filter()
        elif mode == "caid":
            self.open_caid_filter()

    def open_provider_filter(self):
        if self.closed:
            return
            
        provider_counts = {}
        for service in self.all_services:
            if self.current_satellite != "All Satellite":
                if self.current_satellite == "Terrestrial" and service['satellite'] != "Terrestrial":
                    continue
                elif self.current_satellite != "Terrestrial" and self.current_satellite not in service['satellite']:
                    continue
            
            provider = service.get('provider', 'Unknown')
            if provider and provider != "Unknown":
                provider_counts[provider] = provider_counts.get(provider, 0) + 1

        if not provider_counts:
            return
                
        choices = []
        sorted_providers = sorted(provider_counts.items(), key=lambda x: x[0])
        for provider, count in sorted_providers:
            choices.append((f"{provider} - {count} channels", provider))
        
        total_channels = sum(provider_counts.values())
        choices.insert(0, (f"All Providers - {total_channels} channels", "all"))
                
        self.session.openWithCallback(
            self.provider_selected,
            ChoiceBox,
            title=f"Providers on {self.current_satellite}",
            list=choices
        )

    def provider_selected(self, choice):
        if self.closed or not choice or not choice[1]:
            return
        
        if choice[1] == "all":
            self.filter_mode = "All"
            self.filter_provider = None
            self.apply_filters()
            return
            
        self.filter_mode = "Provider"
        self.filter_provider = choice[1]
        self.filter_caid = None
        self.apply_filters()

    def open_caid_filter(self):
        if self.closed:
            return
            
        caid_counts = {}
        active_caid = self.get_active_caid_from_ecm()
        
        for service in self.all_services:
            if self.current_satellite != "All Satellite":
                if self.current_satellite == "Terrestrial" and service['satellite'] != "Terrestrial":
                    continue
                elif self.current_satellite != "Terrestrial" and self.current_satellite not in service['satellite']:
                    continue
            
            caids = self.service_caids.get(service['name'], [])
            for caid in caids:
                caid_counts[caid] = caid_counts.get(caid, 0) + 1

        if not caid_counts:
            return
            
        choices = []
        if active_caid and active_caid in caid_counts:
            count = caid_counts[active_caid]
            choices.append((f"▶ {active_caid} (Active) - {count} channels", active_caid))
            del caid_counts[active_caid]
        
        sorted_caids = sorted(caid_counts.items(), key=lambda x: x[0])
        for caid, count in sorted_caids:
            choices.append((f"{caid} - {count} channels", caid))
        
        total_channels = sum(caid_counts.values())
        choices.append((f"All CAIDs - {total_channels} channels", "all"))
            
        self.session.openWithCallback(
            self.caid_selected,
            ChoiceBox,
            title="Select CAID to filter",
            list=choices
        )

    def caid_selected(self, choice):
        if self.closed or not choice or not choice[1]:
            return
        
        if choice[1] == "all":
            self.filter_mode = "All"
            self.filter_caid = None
            self.apply_filters()
            return
            
        self.filter_mode = "CAID"
        self.filter_caid = choice[1]
        self.filter_provider = None
        self.apply_filters()

    def load_all_bouquets(self):
        if self.closed:
            return
            
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
        
        try:
            self["bouquet_list"].setList(bouquet_display_list)
        except:
            pass

    def bouquet_filter(self):
        if self.closed:
            return
            
        if not self.bouquet_names:
            return
            
        choices = [(name, file) for name, file in self.bouquet_names.items()]
        self.session.openWithCallback(self.bouquet_selected, ChoiceBox, title="Select Bouquet", list=choices)

    def bouquet_selected(self, choice):
        if self.closed or not choice or not choice[1]:
            return

        bouquet_file = choice[1]
        for name, file in self.bouquet_names.items():
            if file == bouquet_file:
                self.current_bouquet = name
                self.current_bouquet_file = file
                self.save_last_used_bouquet(name)  # <-- DODAJ OVU LINIJU
                self.updating = True
                try:
                    self.load_bouquet_channels(file)
                    self["status"].setText(f"Loaded bouquet: {name}")
                finally:
                    self.updating = False
                break

    def load_bouquet_channels(self, bouquet_file):
        if self.closed or self.updating:
            return
            
        self.bouquet_channels = []
        self.bouquet_caids = {}
        self.bouquet_providers = {}
        self.bouquet_refs = {}
        self.bouquet_active_caid = {}
        
        bouquet_path = os.path.join("/etc/enigma2", bouquet_file)
        if not os.path.exists(bouquet_path):
            try:
                self["channels_list"].setList([])
            except:
                pass
            return

        lamedb_services, service_metadata = self.parse_lamedb_with_caids()
        active_caid = self.get_active_caid_from_ecm()
        
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
                    original_line = line
                    
                    if "http" in line.lower() or "9999" in line:
                        channel_name = "Unknown IPTV"
                        if i + 1 < len(lines) and lines[i+1].strip().startswith("#DESCRIPTION"):
                            desc_line = lines[i+1].strip()
                            channel_name = desc_line.replace("#DESCRIPTION", "").strip()
                            i += 1
                        
                        display = f"{channel_name} (IPTV)"
                        self.bouquet_channels.append(display)
                        self.bouquet_caids[channel_name] = []
                        self.bouquet_providers[channel_name] = "IPTV"
                        self.bouquet_refs[channel_name] = original_line
                        i += 1
                        continue

                    else:
                        parts = line.split(":")
                        if len(parts) >= 10:
                            if parts[1] == "64":
                                if i + 1 < len(lines) and lines[i+1].strip().startswith("#DESCRIPTION"):
                                    marker_name = lines[i+1].strip().replace("#DESCRIPTION", "").strip()
                                    display = f"[{marker_name}]"
                                    self.bouquet_channels.append(display)
                                    self.bouquet_refs[marker_name] = original_line
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
                            caids = []
                            provider = "Unknown"
                            
                            for search_key in search_keys:
                                channel_name = lamedb_services.get(search_key)
                                if channel_name:
                                    meta = service_metadata.get(search_key, {})
                                    caids = meta.get("caids", [])
                                    provider = meta.get("provider", "Unknown")
                                    break

                            if not channel_name:
                                channel_name = f"Unknown_{sid}"

                            if active_caid and active_caid in caids:
                                self.bouquet_active_caid[channel_name] = active_caid

                            display = self.format_channel_display(channel_name, caids, active_caid)
                            self.bouquet_channels.append(display)
                            self.bouquet_caids[channel_name] = caids
                            self.bouquet_providers[channel_name] = provider
                            self.bouquet_refs[channel_name] = original_line
                        i += 1
                        
                elif line.startswith("#DESCRIPTION"):
                    marker_name = line.replace("#DESCRIPTION", "").strip()
                    display = f"[{marker_name}]"
                    if display not in self.bouquet_channels:
                        self.bouquet_channels.append(display)
                    i += 1
                else:
                    i += 1

            try:
                self["channels_list"].setList(self.bouquet_channels)
            except:
                pass
        except Exception as e:
            print(f"[CAID Manager] Error loading bouquet: {str(e)}")

    def _auto_save_bouquet(self):
        if not self.current_bouquet_file:
            print("[CAID DEBUG] _auto_save_bouquet prekinut: nema definisanog fajla.")
            return False

        bouquet_path = os.path.join("/etc/enigma2", self.current_bouquet_file)
        print(f"[CAID DEBUG] Otvaram buket za pisanje: {bouquet_path}")
        try:
            new_lines = []
            new_lines.append(f"#NAME {self.current_bouquet}\n")

            for item in self.bouquet_channels:
                if item.startswith("[") and item.endswith("]"):
                    marker_name = item[1:-1]
                    new_lines.append(f"#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
                    new_lines.append(f"#DESCRIPTION {marker_name}\n")
                    continue
                
                channel_name = self.extract_clean_channel_name(item)
                line = self.bouquet_refs.get(channel_name)
                
                print(f"[CAID DEBUG] Fajl planer: Provera za kanal '{channel_name}' -> Dodeljena linija: {line}")
                
                if line:
                    if not line.startswith("#SERVICE"):
                        line = f"#SERVICE {line}"
                    new_lines.append(line + "\n")
                    
                    if " (IPTV)" in item or " (StreamRelay)" in item:
                        clean_desc = channel_name.replace(" (StreamRelay)", "").replace(" (IPTV)", "")
                        new_lines.append(f"#DESCRIPTION {clean_desc}\n")
                else:
                    print(f"[CAID DEBUG] UPOZORENJE: Kanal '{channel_name}' nema skladištenu referencu! Pišem prazan kostur!")
                    new_lines.append(f"#SERVICE 1:0:1:0:0:0:0:0:0:0:\n")
                    new_lines.append(f"#DESCRIPTION {channel_name}\n")

            with open(bouquet_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            print("[CAID DEBUG] Buket uspešno upisan na disk. Osvežavam Enigma2 bazu kanala...")
            try:
                from enigma import eDVBDB
                eDVBDB.getInstance().reloadServicelist()
                eDVBDB.getInstance().reloadBouquets()
                print("[CAID DEBUG] EnigmaDB uspešno osvežen (reloadServicelist / reloadBouquets).")
            except Exception as db_err:
                print(f"[CAID DEBUG] Greška pri osvežavanju EnigmaDB: {str(db_err)}")
                
            return True
        except Exception as e:
            print(f"[CAID DEBUG] Greška unutar _auto_save_bouquet: {str(e)}")
            return False

    def save_bouquet(self):
        if self.closed:
            return
        if not self.current_bouquet_file:
            return
        if self._auto_save_bouquet():
            self["status"].setText("Bouquet saved.")

    def open_main_menu(self):
        if self.closed:
            return
            
        choices = [
            ("Save Current Bouquet", "save"),
            ("Reload All Data", "reload"),
            ("Exit CAID Manager", "exit")
        ]
        
        self.session.openWithCallback(
            self.main_menu_selected,
            ChoiceBox,
            title="CAID Manager - Menu",
            list=choices
        )

    def main_menu_selected(self, choice):
        if self.closed or not choice:
            return
        action = choice[1]
        
        if action == "save":
            self.save_bouquet()
        elif action == "reload":
            self.init_data()
        elif action == "exit":
            self.exit()

    def show_channel_caids(self, panel):
        if self.closed:
            return

        if panel == 0:
            current = self.get_current_service()
        else:
            current = self.get_current_channel()

        if not current:
            return

        channel_name = self.extract_clean_channel_name(current)
        caids = []
        provider = "Unknown"
        active_caid = None

        if panel == 0:
            caids = self.service_caids.get(channel_name, [])
            provider = self.service_providers.get(channel_name, "Unknown")
            active_caid = self.get_active_caid_from_ecm()
        else:
            caids = self.bouquet_caids.get(channel_name, [])
            provider = self.bouquet_providers.get(channel_name, "Unknown")
            active_caid = self.bouquet_active_caid.get(channel_name)

        if not caids:
            self.safe_open_message(
                f"Channel: {channel_name}\nProvider: {provider}\n\nNo CAIDs found.",
                MessageBox.TYPE_INFO,
                timeout=5
            )
            return

        # 1. UKLONI DUPLIKATE
        seen = set()
        unique_caids = []
        for caid in caids:
            if caid not in seen:
                seen.add(caid)
                unique_caids.append(caid)

        # 2. SORTIRAJ: aktivni prvi, ostali po abecedi
        sorted_caids = []
        active_caid_found = None

        if active_caid:
            for caid in unique_caids:
                if caid.upper() == active_caid.upper():
                    active_caid_found = caid
                    break

        if active_caid_found:
            sorted_caids.append(active_caid_found)

        other_caids = [c for c in unique_caids if c != active_caid_found]
        other_caids.sort()
        sorted_caids.extend(other_caids)

        # 3. GRUPIRAJ PO PRVOM ZNAKU (za bolju preglednost)
        groups = {}
        for caid in sorted_caids:
            first_char = caid[0] if caid else "?"
            if first_char not in groups:
                groups[first_char] = []
            groups[first_char].append(caid)

        # 4. FORMATIRAJ SA GRUPAMA
        display_lines = []

        for first_char in sorted(groups.keys()):
            group_caids = groups[first_char]
            # Ako je aktivni u grupi, prikaži ga posebno
            group_display = []
            for caid in group_caids:
                if caid == active_caid_found:
                    group_display.insert(0, f"▶{caid}◀")
                else:
                    group_display.append(caid)

            # Spoji u jedan red
            if len(group_display) <= 4:
                display_lines.append("  ".join(group_display))
            else:
                # Podijeli u redove po 4
                for i in range(0, len(group_display), 4):
                    chunk = group_display[i:i + 4]
                    display_lines.append("  ".join(chunk))

        caid_display = "\n".join(display_lines)

        # Dodaj statistiku
        total = len(sorted_caids)
        if total > 10:
            caid_display += f"\n\nTotal: {total} unique CAIDs"

        message = f"Channel: {channel_name}\nProvider: {provider}\n\nCAIDs:\n{caid_display}"

        timeout = 10 if total <= 10 else 15

        self.safe_open_message(
            message,
            MessageBox.TYPE_INFO,
            timeout=timeout
        )

    def exit(self):
        if self.closed:
            return
        self.closed = True
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        if hasattr(self, 'message_timer'):
            self.message_timer.stop()
        try:
            self.close()
        except:
            pass