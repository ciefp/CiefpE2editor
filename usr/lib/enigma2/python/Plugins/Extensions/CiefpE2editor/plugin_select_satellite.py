# plugin_select_satellite.py
# ============================================================
# CiefpSelectSatellite - Satellite Selector
# Omogućava korisniku da selektuje satelite i kreira prilagođenu listu
# ============================================================

import os
import re
import shutil
import zipfile
import requests
from xml.etree import ElementTree
from enigma import eConsoleAppContainer, eDVBDB
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import fileExists

# ============================================================
# GLOBALNE VARIJABLE
# ============================================================

PLUGIN_VERSION = "1.8"
PLUGIN_ICON = "plugin.png"
PLUGIN_NAME = "CiefpSelectSatellite"
TMP_DOWNLOAD = "/tmp/ciefp-E2-75E-34W"
TMP_SELECTED = "/tmp/CiefpSelectSatellite"
GITHUB_API_URL = "https://api.github.com/repos/ciefp/ciefpsettings-enigma2-zipped/contents/"
STATIC_NAMES = ["ciefp-E2-75E-34W"]

debug_file = "/tmp/ciefp_e2editor_debug.log"

def log_debug(message):
    try:
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(f"[SELECT_SAT] {message}\n")
    except:
        pass


class CiefpSelectSatellite(Screen):
    """Satellite Selector - Kreiranje prilagođene liste kanala"""
    
    skin = """
        <screen position="center,center" size="1920,1080" title="..:: Ciefp Satellite Selector ::.." backgroundColor="#011a2e">
            <widget name="title" position="0,20" size="1920,50" font="Bold;40" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="..:: Satellite Selector ::.." />
            
            <widget name="left_list" position="50,90" size="600,858" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;26" backgroundColor="#011a2e" />
            <widget name="right_list" position="650,90" size="600,858" scrollbarMode="showOnDemand" itemHeight="33" font="Regular;26" backgroundColor="#011a2e" />
            <widget name="background" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/background.png" position="1300,90" size="600,800" />
            
            <widget name="status" position="50,960" size="1920,40" font="Regular;24" foregroundColor="#00FF00" backgroundColor="#012e01" />
            
            <widget name="red_button" position="50,1010" size="180,40" font="Bold;28" halign="center" backgroundColor="#9F1313" foregroundColor="#FFFFFF" text="Exit" />
            <widget name="green_button" position="240,1010" size="180,40" font="Bold;28" halign="center" backgroundColor="#1F771F" foregroundColor="#FFFFFF" text="Copy" />
            <widget name="yellow_button" position="430,1010" size="180,40" font="Bold;28" halign="center" backgroundColor="#9F9F13" foregroundColor="#000000" text="Install" />
            <widget name="blue_button" position="620,1010" size="180,40" font="Bold;28" halign="center" backgroundColor="#1F1F77" foregroundColor="#FFFFFF" text="Update" />
            
            <widget name="info" position="900,1010" size="950,40" font="Regular;24" halign="right" foregroundColor="#00FF00" backgroundColor="#011a2e" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.selected_satellites = []
        self.bouquet_mapping = self.create_bouquet_mapping()
        
        # Widgeti
        self["title"] = Label("Satellite Selector")
        self["left_list"] = MenuList([])
        self["right_list"] = MenuList([])
        self["background"] = Pixmap()
        self["status"] = Label("Initializing...")
        self["red_button"] = Label("Exit")
        self["green_button"] = Label("Copy")
        self["yellow_button"] = Label("Install")
        self["blue_button"] = Label("Update")
        self["info"] = Label(f"v{PLUGIN_VERSION}")
        
        # Akcije
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.select_item,
                "cancel": self.exit,
                "green": self.copy_files,
                "yellow": self.install,
                "red": self.exit,
                "blue": self.confirm_update,
                "up": self.up,
                "down": self.down,
                "left": self.switch_left,
                "right": self.switch_right,
            },
            -1
        )
        
        self.onLayoutFinish.append(self.fetch_version_info)
        self.download_settings()

    def create_bouquet_mapping(self):
        """Kreiraj mapiranje satelita -> bouquet fajlovi"""
        return {
            '80.0E': ['userbouquet.ciefp_80e.tv'],
            '75.0E': ['userbouquet.ciefp_68e.tv'],
            '70.5E': ['userbouquet.ciefp_68e.tv'],
            '68.5E': ['userbouquet.ciefp_68e.tv'],
            '66.0E': ['userbouquet.ciefp_62e.tv'],
            '62.0E': ['userbouquet.ciefp_62e.tv'],
            '54.9E': ['userbouquet.ciefp_55e.tv'],
            '53.0E': ['userbouquet.ciefp_53e.tv'],
            '52.5E': ['userbouquet.ciefp_53e.tv'],
            '52.0E': ['userbouquet.ciefp_52e.tv', 'userbouquet.ciefp_52e_aref.tv'],
            '51.5E': ['userbouquet.ciefp_51e.tv'],
            '46.0E': ['userbouquet.ciefp_46e.tv'],
            '45.0E': ['userbouquet.ciefp_45e.tv', 'userbouquet.ciefp_45e_vivacom.tv'],
            '42.0E': ['userbouquet.ciefp_42e_turksat.tv', 'userbouquet.ciefp_42e_digiturk.tv', 
                      'userbouquet.ciefp_42e_dsmart.tv', 'userbouquet.ciefp_42e_tivibu.tv'],
            '39.0E': ['userbouquet.ciefp_39e_hellas.tv', 'userbouquet.ciefp_39e_hellas_sport.tv',
                      'userbouquet.ciefp_39e_ert.tv', 'userbouquet.ciefp_39e_polaris.tv',
                      'userbouquet.ciefp_39e_dolce.tv', 'userbouquet.ciefp_39e_a1bg.tv'],
            '36.0E': ['userbouquet.ciefp_36e.tv'],
            '31.0E': ['userbouquet.ciefp_31e.tv'],
            '28.2E': ['userbouquet.ciefp_28e_astra.tv', 'userbouquet.ciefp_28e_skyuk_icam.tv',
                      'userbouquet.ciefp_28e_skyukmovie.tv', 'userbouquet.ciefp_28e_skyukdocuments.tv',
                      'userbouquet.ciefp_28e_skyuksports.tv', 'userbouquet.ciefp_28e_skyukkids.tv',
                      'userbouquet.ciefp_28e_skyukgeneral.tv'],
            '26.0E': ['userbouquet.ciefp_26e_badr.tv', 'userbouquet.ciefp_26e_mbc.tv'],
            '23.5E': ['userbouquet.ciefp_23e_astra.tv', 'userbouquet.ciefp_23e_skylinkgeneral.tv',
                      'userbouquet.ciefp_23e_skylink.tv', 'userbouquet.ciefp_23e_canaldigital.tv',
                      'userbouquet.ciefp_23e_sport.tv', 'userbouquet.ciefp_23e_telekomsrbija.tv'],
            '21.5E': ['userbouquet.ciefp_21e_eutelsat.tv'],
            '19.2E': ['userbouquet.ciefp_19e_astra.tv', 'userbouquet.ciefp_19e_movistarsport.tv',
                      'userbouquet.ciefp_19e_movistarmovies.tv', 'userbouquet.ciefp_19e_movistardocu.tv',
                      'userbouquet.ciefp_19e_skyde_icam.tv', 'userbouquet.ciefp_19e_skydemovies.tv',
                      'userbouquet.ciefp_19e_skydedocu.tv', 'userbouquet.ciefp_19e_skydesport.tv',
                      'userbouquet.ciefp_19e_hdplus.tv', 'userbouquet.ciefp_19e_ORF.tv',
                      'userbouquet.ciefp_19e_fta.tv', 'userbouquet.ciefp_19e_canaldigitaal.tv',
                      'userbouquet.ciefp_19e_canalsat.tv'],
            '16.1E': ['userbouquet.ciefp_16e_rtsh.tv'],
            '16.0E': ['userbouquet.ciefp_16e_eutelsat.tv', 'userbouquet.ciefp_16e_oivzagreb.tv',
                      'userbouquet.ciefp_16e_maxtv.tv', 'userbouquet.ciefp_16e_pink.tv',
                      'userbouquet.ciefp_16e_antiksat.tv', 'userbouquet.ciefp_16e_sport.tv',
                      'userbouquet.ciefp_16e_totaltv.tv', 'userbouquet.ciefp_16e_vipnet.tv',
                      'userbouquet.ciefp_16e_digitalbania.tv', 'userbouquet.ciefp_16e_freesatromania.tv'],
            '13.0E': ['userbouquet.ciefp_13e_hotbird.tv', 'userbouquet.ciefp_13e_polandmovies.tv',
                      'userbouquet.ciefp_13e_polanddocu.tv', 'userbouquet.ciefp_13e_polandgeneral.tv',
                      'userbouquet.ciefp_13e_polandsport.tv', 'userbouquet.ciefp_13e_sfi.tv',
                      'userbouquet.ciefp_13e_orangefrance.tv', 'userbouquet.ciefp_13e_raimediaset.tv',
                      'userbouquet.ciefp_13e_vivacom.tv', 'userbouquet.ciefp_13e_skyitaliahd.tv',
                      'userbouquet.ciefp_13e_skyitalia_icam.tv', 'userbouquet.ciefp_13e_novagreece.tv'],
            '10.0E': ['userbouquet.ciefp_10e_eutelsat.tv'],
            '9.0E': ['userbouquet.ciefp_9e_eutelsat.tv', 'userbouquet.ciefp_9e_kabelkiosk.tv',
                     'userbouquet.ciefp_9e_cosmote.tv', 'userbouquet.ciefp_9e_afn.tv',
                     'userbouquet.ciefp_9e_mediaset.tv', 'userbouquet.ciefp_9e_persidera.tv'],
            '7.0E': ['userbouquet.ciefp_7e_eutelsat.tv'],
            '4.8E': ['userbouquet.ciefp_5e_fta_powervu.tv', 'userbouquet.ciefp_5e_ukraina.tv',
                     'userbouquet.ciefp_5e_brt_t2mi.tv'],
            '3.0E': ['userbouquet.ciefp_3e_eutelsat.tv'],
            '1.9E': ['userbouquet.ciefp_2e_bulgariasat1.tv', 'userbouquet.ciefp_2e_neosat.tv'],
            '0.8W': ['userbouquet.ciefp_08w_thor.tv', 'userbouquet.ciefp_08w_sport.tv',
                     'userbouquet.ciefp_08w_docu.tv', 'userbouquet.ciefp_08w_music.tv',
                     'userbouquet.ciefp_08w_allente_sve_den.tv', 'userbouquet.ciefp_08w_allente_movie_music.tv',
                     'userbouquet.ciefp_08w_directone_svk.tv', 'userbouquet.ciefp_08w_directone_movies.tv',
                     'userbouquet.ciefp_08w_focussat.tv', 'userbouquet.ciefp_08w_focussat_movies.tv',
                     'userbouquet.ciefp_08w_digitv.tv', 'userbouquet.ciefp_08w_slovaktelekom.tv'],
            '4.0W': ['userbouquet.ciefp_4w_amos.tv'],
            '5.0W': ['userbouquet.ciefp_5w_eutelsat.tv', 'userbouquet.ciefp_5w_rai.tv',
                     'userbouquet.ciefp_5w_france_multistream.tv', 'userbouquet.ciefp_5w_francesat.tv'],
            '7.0W': ['userbouquet.ciefp_7w.tv'],
            '14.0W': ['userbouquet.ciefp_14w.tv'],
            '22.0W': ['userbouquet.ciefp_15w.tv'],
            '24.5W': ['userbouquet.ciefp_15w.tv'],
            '30.0W': ['userbouquet.ciefp_30w_hispasat.tv', 'userbouquet.ciefp_30w_hispasatsport.tv',
                      'userbouquet.ciefp_30w_nos.tv', 'userbouquet.ciefp_30w_meotv.tv',
                      'userbouquet.ciefp_30w_abertis.tv'],
            '34.5W': ['userbouquet.ciefp_35w.tv'],
            'DVBT/T2': ['userbouquet.ciefp_terrestrial_fta.tv', 'userbouquet.ciefp_terrestrial_paytv.tv']
        }

    def find_satellite_bouquet(self, satellite_name):
        """Pronađi bouquet fajlove za dati satelit"""
        match = re.search(r'(\d+\.\d+[EW])', satellite_name)
        if match:
            position = match.group(1)
            if position in self.bouquet_mapping:
                return self.bouquet_mapping[position]
        return None

    def parse_satellites(self):
        """Parsiraj satellites.xml i prikaži satelite u lijevoj listi"""
        xml_path = os.path.join(TMP_DOWNLOAD, "satellites.xml")
        if not fileExists(xml_path):
            self["status"].setText("Error: satellites.xml not found!")
            return
        
        try:
            with open(xml_path, 'r', encoding='iso-8859-1') as f:
                xml_content = f.read()
            
            root = ElementTree.fromstring(xml_content)
            satellites = [sat.get('name') for sat in root.findall('sat')]
            
            # Filter satelita - samo oni koji imaju bouquet mapping
            filtered_satellites = []
            for sat in satellites:
                for key in self.bouquet_mapping.keys():
                    if key in sat:
                        filtered_satellites.append(sat)
                        break
            
            self["left_list"].setList(filtered_satellites)
            self["status"].setText(f"Satellites loaded successfully. ({len(filtered_satellites)} found)")
            log_debug(f"Loaded {len(filtered_satellites)} satellites")
            
        except Exception as e:
            self["status"].setText(f"Error parsing XML: {str(e)}")
            log_debug(f"Error parsing XML: {str(e)}")

    def download_settings(self):
        """Preuzmi najnovije podešavanje sa GitHub-a"""
        self["status"].setText("Fetching file list from GitHub...")
        
        try:
            response = requests.get(GITHUB_API_URL, timeout=10)
            response.raise_for_status()
            files = response.json()
            
            zip_url = None
            for file in files:
                if any(name in file["name"] for name in STATIC_NAMES) and file["name"].endswith(".zip"):
                    zip_url = file["download_url"]
                    break
            
            if not zip_url:
                raise Exception("No matching ZIP file found on GitHub.")
            
            self["status"].setText("Downloading settings from GitHub...")
            zip_path = os.path.join("/tmp", "latest.zip")
            zip_response = requests.get(zip_url, timeout=30)
            
            with open(zip_path, 'wb') as f:
                f.write(zip_response.content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                temp_extract_path = "/tmp/temp_extract"
                if not os.path.exists(temp_extract_path):
                    os.makedirs(temp_extract_path)
                zip_ref.extractall(temp_extract_path)
                
                extracted_items = os.listdir(temp_extract_path)
                if extracted_items:
                    extracted_root = os.path.join(temp_extract_path, extracted_items[0])
                    if os.path.exists(TMP_DOWNLOAD):
                        shutil.rmtree(TMP_DOWNLOAD)
                    shutil.move(extracted_root, TMP_DOWNLOAD)
            
            self["status"].setText("Settings downloaded and extracted successfully.")
            self.parse_satellites()
            
        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            log_debug(f"Download error: {str(e)}")

    def fetch_version_info(self):
        """Dohvati informaciju o verziji liste"""
        try:
            response = requests.get(GITHUB_API_URL, timeout=5)
            response.raise_for_status()
            files = response.json()
            
            for file in files:
                if any(name in file["name"] for name in STATIC_NAMES) and file["name"].endswith(".zip"):
                    version_with_date = file["name"].replace(".zip", "")
                    self["info"].setText(f"List: {version_with_date}")
                    return
            
            self["info"].setText("List: (Date not available)")
        except Exception as e:
            log_debug(f"Error fetching version: {str(e)}")
            self["info"].setText("List: (Error fetching date)")

    def select_item(self):
        """Selektuj/odselektuj satelit"""
        selected = self["left_list"].getCurrent()
        if not selected:
            return
        
        # Provjeri da li je satelit već selektovan
        if selected in self.selected_satellites:
            self.selected_satellites.remove(selected)
            log_debug(f"Removed satellite: {selected}")
        else:
            self.selected_satellites.append(selected)
            log_debug(f"Added satellite: {selected}")
        
        self["right_list"].setList(self.selected_satellites)
        self["status"].setText(f"Selected {len(self.selected_satellites)} satellites")

    def copy_files(self):
        """Kopiraj selektovane fajlove u tmp folder"""
        try:
            if not os.path.exists(TMP_SELECTED):
                os.makedirs(TMP_SELECTED)
            
            # Lista zajedničkih fajlova
            common_files = [
                'satellites.xml', 'lamedb', 'bouquets.tv',
                'userbouquet.buket_exyu.tv', 'userbouquet.buket_pinktv.tv',
                'userbouquet.buket_maxtv.tv', 'userbouquet.buket_sport.tv',
                'userbouquet.buket_kids.tv', 'userbouquet.buket_docu.tv',
                'userbouquet.buket_movie.tv', 'userbouquet.buket_music.tv',
                'userbouquet.buket_uhd.tv', 'userbouquet.buket_adult.tv',
                'userbouquet.buket_multistream.tv', 'userbouquet.buket_emu.tv',
                'userbouquet.marker_vod_exyu.tv', 'userbouquet.ciefp_terrestrial_fta.tv',
                'userbouquet.ciefp_terrestrial_paytv.tv', 'bouquets.radio',
                'userbouquet.dbe00.radio', 'userbouquet.favourites.radio',
                'userbouquet.LastScanned.tv', 'userbouquet.favourites.tv'
            ]
            
            # Kopiranje zajedničkih fajlova
            copied = 0
            for f in common_files:
                src = os.path.join(TMP_DOWNLOAD, f)
                if os.path.exists(src):
                    shutil.copy(src, TMP_SELECTED)
                    copied += 1
            
            # Kopiranje buketa za selektovane satelite
            for sat in self.selected_satellites:
                bouquets = self.find_satellite_bouquet(sat)
                if bouquets:
                    for bouquet_file in bouquets:
                        src = os.path.join(TMP_DOWNLOAD, bouquet_file)
                        if os.path.exists(src):
                            shutil.copy(src, TMP_SELECTED)
                            copied += 1
            
            self["status"].setText(f"Files copied successfully! ({copied} files)")
            log_debug(f"Copied {copied} files to {TMP_SELECTED}")
            
        except Exception as e:
            self["status"].setText(f"Copy error: {str(e)}")
            log_debug(f"Copy error: {str(e)}")

    def install(self):
        """Instaliraj selektovane satelite"""
        if not self.selected_satellites:
            self.session.open(MessageBox, "No satellites selected!", MessageBox.TYPE_ERROR)
            return
        
        self.session.openWithCallback(
            self.install_confirmed,
            MessageBox,
            f"Install {len(self.selected_satellites)} selected satellites?",
            MessageBox.TYPE_YESNO
        )

    def install_confirmed(self, result):
        """Potvrda instalacije"""
        if not result:
            return
        
        try:
            enigma2_dir = "/etc/enigma2"
            tuxbox_dir = "/etc/tuxbox"
            source_dir = TMP_SELECTED
            
            if not os.path.exists(source_dir) or not os.listdir(source_dir):
                self["status"].setText("Error: No files to install!")
                return
            
            self["status"].setText("Installing selected satellites...")
            
            # Kopiraj zajedničke fajlove
            for f in os.listdir(source_dir):
                src = os.path.join(source_dir, f)
                if f == "satellites.xml":
                    shutil.copy(src, tuxbox_dir)
                elif f.endswith(('.tv', '.radio', 'lamedb')):
                    shutil.copy(src, enigma2_dir)
            
            # Reload Enigma2
            self.reload_settings()
            self["status"].setText("Installation successful!")
            log_debug("Installation completed successfully")
            
        except Exception as e:
            self["status"].setText(f"Error: {str(e)}")
            log_debug(f"Install error: {str(e)}")

    def reload_settings(self):
        """Reload Enigma2 settings"""
        try:
            eDVBDB.getInstance().reloadServicelist()
            eDVBDB.getInstance().reloadBouquets()
            self.session.open(
                MessageBox,
                "Reload successful! New settings are now active.",
                MessageBox.TYPE_INFO,
                timeout=5
            )
        except Exception as e:
            self.session.open(
                MessageBox,
                f"Reload failed: {str(e)}",
                MessageBox.TYPE_ERROR,
                timeout=5
            )

    def confirm_update(self):
        """Potvrdi update plugina"""
        self.session.openWithCallback(
            self.prompt_update,
            MessageBox,
            "Do you want to update the plugin?",
            MessageBox.TYPE_YESNO
        )

    def prompt_update(self, answer):
        """Izvrši update"""
        if answer:
            self.update_plugin()

    def update_plugin(self):
        """Update plugin sa GitHub-a"""
        self["status"].setText("Updating plugin...")
        cmd = "wget -q --no-check-certificate https://raw.githubusercontent.com/ciefp/CiefpSelectSatellite/main/installer.sh -O - | /bin/sh"
        
        container = eConsoleAppContainer()
        container.execute(cmd)
        self["status"].setText("Update completed. Please restart Enigma2.")

    def up(self):
        """Kretanje gore"""
        self["left_list"].up()

    def down(self):
        """Kretanje dole"""
        self["left_list"].down()

    def switch_left(self):
        """Fokus na lijevu listu"""
        self["left_list"].setFocus(True)
        self["right_list"].setFocus(False)
        self["status"].setText("Focus: Satellite list")

    def switch_right(self):
        """Fokus na desnu listu"""
        self["left_list"].setFocus(False)
        self["right_list"].setFocus(True)
        self["status"].setText("Focus: Selected satellites list")

    def exit(self):
        """Izlaz"""
        log_debug("Exiting CiefpSelectSatellite")
        self.close()


# ============================================================
# Plugin registracija (ako se koristi samostalno)
# ============================================================

def main(session, **kwargs):
    session.open(CiefpSelectSatellite)

def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name="CiefpSelectSatellite",
            description="Select satellite to install",
            icon="plugin.png",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            fnc=main
        )
    ]