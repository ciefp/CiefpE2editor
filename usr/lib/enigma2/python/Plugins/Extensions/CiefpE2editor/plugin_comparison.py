from __future__ import absolute_import
import os
import re
import requests
from datetime import datetime
from Components.Pixmap import Pixmap
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel

# =====================================================================
# KONFIGURACIJA
# =====================================================================
GITHUB_REPO = "ciefp/ciefpsettings-enigma2"
GITHUB_BRANCH = "master"

AVAILABLE_FOLDERS = [
    "ciefp-E2-1sat-19E",
    "ciefp-E2-2satA-19E-13E",
    "ciefp-E2-2satB-19E-16E",
    "ciefp-E2-3satA-9E-10E-13E",
    "ciefp-E2-3satB-19E-16E-13E",
    "ciefp-E2-4satA-28E-19E-13E-30W",
    "ciefp-E2-4satB-19E-16E-13E-0.8W",
    "ciefp-E2-5sat-19E-16E-13E-1.9E-0.8W",
    "ciefp-E2-6sat-23E-19E-16E-13E-1.9E-0.8W",
    "ciefp-E2-7sat-23E-19E-16E-13E-4.8E-1.9E-0.8W",
    "ciefp-E2-8sat-28E-23E-19E-16E-13E-4.8E-1.9E-0.8W",
    "ciefp-E2-9sat-28E-23E-19E-16E-13E-9E-1.9E-0.8W-5W",
    "ciefp-E2-10sat-39E-28E-23E-19E-16E-13E-9E-4.8E-1.9E-0.8W",
    "ciefp-E2-13sat-42E-39E-28E-23E-19E-16E-13E-9E-7E-4.8E-1.9E-0.8w-5w",
    "ciefp-E2-16sat-42E-39E-28E-26E-23E-19E-16E-13E-10E-9E-7E-4.8E-1.9E-0.8w-4W-5w",
    "ciefp-E2-18sat-42E-39E-36E-33E-28E-26E-23E-19E-16E-13E-10E-9E-7E-4.8E-1.9E-0.8w-4W-5w",
    "ciefp-E2-motor-75E-34W",
]

DEFAULT_FOLDER = "ciefp-E2-motor-75E-34W"

LOCAL_BOUQUETS_DIR = "/etc/enigma2/"
LOCAL_VERSION_FILE = "/etc/enigma2/userbouquet.buket_sport.tv"
LOCAL_LAMEDB_FILE = "/etc/enigma2/lamedb"

IGNORED_BOUQUETS = {
    "userbouquet.LastScanned.tv",
    "userbouquet.LastScanned.radio",
}

MAX_SERVICES_PER_BOUQUET = 20


# =====================================================================
# POMOĆNE FUNKCIJE
# =====================================================================
def to_unicode(s):
    try:
        return s.decode('utf-8') if isinstance(s, bytes) else str(s)
    except Exception:
        return str(s)


def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%d.%m.%Y")
    except (ValueError, TypeError):
        return None


# ---------------------- LOKALNI PODACI ----------------------
def get_local_version():
    if not os.path.exists(LOCAL_VERSION_FILE):
        return None
    try:
        with open(LOCAL_VERSION_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            first = f.readline()
        m = re.search(r'(\d{2}\.\d{2}\.\d{4})', first)
        return m.group(1) if m else None
    except Exception:
        return None


def get_local_bouquets():
    result = {}
    if not os.path.isdir(LOCAL_BOUQUETS_DIR):
        return result
    for fn in os.listdir(LOCAL_BOUQUETS_DIR):
        if fn.startswith("userbouquet.") and (fn.endswith(".tv") or fn.endswith(".radio")):
            result[fn] = os.path.join(LOCAL_BOUQUETS_DIR, fn)
    return result


def load_local_lamedb():
    try:
        with open(LOCAL_LAMEDB_FILE, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


# ---------------------- REMOTE PODACI ----------------------
def fetch_remote_bouquets(folder):
    api_url = "https://api.github.com/repos/{0}/contents/{1}".format(GITHUB_REPO, folder)
    headers = {"Accept": "application/vnd.github.v3+json"}
    r = requests.get(api_url, headers=headers, timeout=15)
    r.raise_for_status()
    items = r.json()

    result = {}
    for item in items:
        name = item.get("name", "")
        if not (name.startswith("userbouquet.") and
                (name.endswith(".tv") or name.endswith(".radio"))):
            continue
        download_url = item.get("download_url")
        if not download_url:
            continue
        try:
            rr = requests.get(download_url, timeout=20)
            rr.raise_for_status()
            result[name] = rr.text
        except Exception:
            result[name] = ""
    return result


def fetch_remote_version(folder):
    url = "https://raw.githubusercontent.com/{0}/{1}/{2}/userbouquet.buket_sport.tv".format(
        GITHUB_REPO, GITHUB_BRANCH, folder)
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            first = r.text.split("\n", 1)[0]
            m = re.search(r'(\d{2}\.\d{2}\.\d{4})', first)
            return m.group(1) if m else None
    except Exception:
        pass
    return None


def fetch_remote_lamedb(folder):
    url = "https://raw.githubusercontent.com/{0}/{1}/{2}/lamedb".format(
        GITHUB_REPO, GITHUB_BRANCH, folder)
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""


# ---------------------- PARSERI BUKETA ----------------------
def read_bouquet_name(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            first = f.readline().strip()
        if first.startswith("#NAME"):
            return first.replace("#NAME", "", 1).strip()
    except Exception:
        pass
    return ""


def read_bouquet_name_from_text(text):
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#NAME"):
            return line.replace("#NAME", "", 1).strip()
        if line:
            break
    return ""


def read_bouquet_services(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        return _parse_bouquet_services_text(text)
    except Exception:
        return set()


def read_bouquet_services_from_text(text):
    return _parse_bouquet_services_text(text)


def _parse_bouquet_services_text(text):
    """
    Vraća set 'normalizovanih' servisa:
    - Marker: 'MARKER::naziv'
    - Ostalo: puna #SERVICE linija
    """
    services = set()
    if not text:
        return services

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("#SERVICE"):
            parts = line.split(":")

            # Marker? (service type == 64)
            if len(parts) >= 2 and parts[1] == "64":
                marker_name = ""
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if nxt.startswith("#DESCRIPTION"):
                        marker_name = nxt.replace("#DESCRIPTION", "", 1).strip()
                services.add("MARKER::{0}".format(marker_name))
                i += 2
                continue

            services.add(line)
        i += 1

    return services


# =====================================================================
# LAMEDB PARSER — PREUZET IZ plugin.py (CiefpE2editorMain.parse_lamedb)
# =====================================================================
def parse_lamedb(text):
    """
    Parsira lamedb i vraća dict: ključ -> ime kanala.
    Ključevi su:
      'SID:namespace:TSID:ONID'   (original)
      'SID:namespace:TSID:ONID'   (bez vodećih nula)
    """
    services = {}

    if not text:
        return services

    start_idx = text.find("\nservices\n")
    end_idx = text.find("\nend\n", start_idx)
    if start_idx == -1 or end_idx == -1:
        return services

    services_block = text[start_idx + 10:end_idx]
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

                key1 = "{0}:{1}:{2}:{3}".format(sid, satfreq, tsid, onid)
                key2 = "{0}:{1}:{2}:{3}".format(
                    sid.lstrip('0') or '0',
                    satfreq,
                    tsid.lstrip('0') or '0',
                    onid.lstrip('0') or '0'
                )

                name = ""
                if i + 1 < len(lines):
                    name = lines[i + 1].strip()

                if name and not name.startswith("p:") and not name.startswith("c:"):
                    services[key1] = name
                    services[key2] = name

                i += 2
                continue
        i += 1

    return services


def service_to_name(line, lamedb_map):
    """
    Vraća lepo ime za servis liniju:
    - MARKER::xxx -> [MARKER] xxx
    - StreamRelay/IPTV -> ime iza zadnjeg ':'
    - Standard -> iz lamedb mape (koristi istu logiku kao load_bouquet_channels)
    - Fallback -> puna linija
    """
    # Marker
    if line.startswith("MARKER::"):
        return "[MARKER] {0}".format(line.replace("MARKER::", "", 1))

    if not line.startswith("#SERVICE"):
        return line

    parts = line.split(":")

    # Marker (type 64)
    if len(parts) >= 2 and parts[1] == "64":
        return line

    # StreamRelay / IPTV - ime iza zadnjeg ':'
    if "http" in line.lower() or "4097:" in line or "5001:" in line or "5002:" in line:
        last_colon = line.rfind(":")
        if last_colon != -1 and last_colon < len(line) - 1:
            name = line[last_colon + 1:].strip()
            if name and not name.startswith("//"):
                return name
        return line

    # Standardni servis — koristi istu logiku kao u plugin.py
    if len(parts) >= 10:
        try:
            sid = parts[3]
            tsid = parts[4]
            onid = parts[5]
            satfreq = parts[6].lower()
            satfreq = "00{0}".format(satfreq) if len(satfreq) == 6 else satfreq.zfill(8)

            search_keys = [
                "{0}:{1}:{2}:{3}".format(
                    int(sid, 16), satfreq, int(tsid, 16), int(onid, 16)
                ),
                "{0}:{1}:{2}:{3}".format(
                    sid.lower(), satfreq, tsid.lower(), onid.lower()
                ),
                "{0}:{1}:{2}:{3}".format(
                    "{0:04x}".format(int(sid, 16)),
                    satfreq,
                    "{0:04x}".format(int(tsid, 16)),
                    "{0:04x}".format(int(onid, 16))
                ),
            ]

            for key in search_keys:
                if key in lamedb_map:
                    return lamedb_map[key]

            # Probaj i sa key2 formatom (bez vodećih nula)
            for key in search_keys:
                p = key.split(":")
                k2 = "{0}:{1}:{2}:{3}".format(
                    p[0].lstrip('0') or '0',
                    p[1],
                    p[2].lstrip('0') or '0',
                    p[3].lstrip('0') or '0'
                )
                if k2 in lamedb_map:
                    return lamedb_map[k2]

        except Exception:
            pass

    return line


# =====================================================================
# GLAVNI SCREEN
# =====================================================================
class CiefpComparisonScreen(Screen):
    skin = """
        <screen name="CiefpComparisonScreen" position="center,center" size="1920,1080" backgroundColor="#011a2e">
            <widget name="separator0" position="0,5" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="plugin_title" position="0,10" size="1920,50" font="Bold;30" halign="center" backgroundColor="#012e01" foregroundColor="#FFFFFF" text="..:: Ciefp Settings Comparison ::.." />
            <widget name="separator1" position="0,65" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="version_info" position="0,75" size="1920,50" font="Bold;28" halign="center" backgroundColor="#011a2e" foregroundColor="#00FFFF" />
            <widget name="separator2" position="0,130" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />

            <!-- Report sa leve strane -->
            <widget name="result" position="40,140" size="1250,800" font="Regular;24" backgroundColor="#011a2e" foregroundColor="#FFFFFF" transparent="1" zPosition="1" />

            <!-- Logo sa desne strane -->
            <widget name="logo" position="1300,140" size="600,800" zPosition="1" alphatest="on" />

            <widget name="separator3" position="0,945" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="status" position="40,950" size="1840,40" font="Regular;24" halign="center" foregroundColor="#00FF00" backgroundColor="#011a2e" />
            <widget name="separator4" position="0,995" size="1920,3" backgroundColor="#d5fa02" zPosition="1" />
            <widget name="red_button" position="20,1005" size="460,40" font="Bold;26" halign="center" backgroundColor="#9F1313" foregroundColor="#FFFFFF" text="Back" />
            <widget name="green_button" position="490,1005" size="460,40" font="Bold;26" halign="center" backgroundColor="#1F771F" foregroundColor="#FFFFFF" text="Re-run" />
            <widget name="yellow_button" position="960,1005" size="460,40" font="Bold;26" halign="center" backgroundColor="#A0A000" foregroundColor="#FFFFFF" text="Save Report" />
            <widget name="blue_button" position="1430,1005" size="470,40" font="Bold;26" halign="center" backgroundColor="#1313A0" foregroundColor="#FFFFFF" text="Select Folder" />
        </screen>
    """
    def __init__(self, session, folder=DEFAULT_FOLDER):
        Screen.__init__(self, session)
        self.session = session
        self.folder = folder

        self["plugin_title"] = Label("..:: Ciefp Settings Comparison ::..")
        self["version_info"] = Label("")
        self["result"] = ScrollLabel("")
        self["status"] = Label("")
        self["logo"] = Pixmap()
        self["red_button"] = Label("Back")
        self["green_button"] = Label("Re-run")
        self["yellow_button"] = Label("Save Report")
        self["blue_button"] = Label("Select Folder")
        self["separator0"] = Label()
        self["separator1"] = Label()
        self["separator2"] = Label()
        self["separator3"] = Label()
        self["separator4"] = Label()

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.close,
                "cancel": self.close,
                "red": self.close,
                "green": self.run_comparison,
                "yellow": self.save_report,
                "blue": self.select_folder,
                "up": self["result"].pageUp,
                "down": self["result"].pageDown,
                "left": self["result"].pageUp,
                "right": self["result"].pageDown,
            }, -1
        )

        self.report_text = ""
        self.local_lamedb = {}
        self.remote_lamedb = {}
        self.onLayoutFinish.append(self.run_comparison)
        self.onLayoutFinish.append(self.load_logo)

    # -----------------------------------------------------------------
    def select_folder(self):
        choices = [(name, name) for name in AVAILABLE_FOLDERS]
        self.session.openWithCallback(
            self.folder_selected,
            ChoiceBox,
            title="Select settings folder to compare with",
            list=choices
        )

    def folder_selected(self, choice):
        if choice and choice[1]:
            self.folder = choice[1]
            self.run_comparison()

    # -----------------------------------------------------------------
    def load_logo(self):
        """Učitava logo plugina sa desne strane."""
        # Probaj više puta lokacija
        logo_paths = [
            "/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/comparison_logo.png",
            "/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/logo.png",
            "/usr/lib/enigma2/python/Plugins/Extensions/CiefpE2editor/icon.png",
        ]
        for path in logo_paths:
            if os.path.exists(path):
                try:
                    self["logo"].instance.setPixmapFromFile(path)
                    return
                except Exception as e:
                    print("[CiefpComparison] logo load error: {0}".format(to_unicode(str(e))))
        # Ako nema logotipa, sakrij widget
        try:
            self["logo"].hide()
        except Exception:
            pass

    # -----------------------------------------------------------------
    def run_comparison(self):
        self["status"].setText("Reading local settings...")
        local_version = get_local_version()
        local_bouquets = get_local_bouquets()

        if not local_bouquets:
            self["status"].setText("No local bouquets found in /etc/enigma2/")
            return

        self["status"].setText("Loading lamedb files...")
        try:
            local_lamedb_text = load_local_lamedb()
            self.local_lamedb = parse_lamedb(local_lamedb_text)
            print("[CiefpComparison] local lamedb entries: {0}".format(len(self.local_lamedb)))
        except Exception as e:
            print("[CiefpComparison] local lamedb error: {0}".format(to_unicode(str(e))))
            self.local_lamedb = {}

        self["status"].setText("Fetching remote from GitHub ({0})...".format(self.folder))
        try:
            remote_version = fetch_remote_version(self.folder)
            remote_bouquets_raw = fetch_remote_bouquets(self.folder)
            remote_lamedb_text = fetch_remote_lamedb(self.folder)
            self.remote_lamedb = parse_lamedb(remote_lamedb_text)
            print("[CiefpComparison] remote lamedb entries: {0}".format(len(self.remote_lamedb)))
        except Exception as e:
            self["status"].setText("Error: " + to_unicode(str(e)))
            return

        if not remote_bouquets_raw:
            self["status"].setText("No remote bouquets found in folder " + self.folder)
            return

        # --- Odredi smer poređenja ---
        local_date = parse_date(local_version)
        remote_date = parse_date(remote_version)

        if local_date and remote_date and local_date >= remote_date:
            old_label = "GitHub: {0}".format(remote_version or "?")
            new_label = "Local: {0}".format(local_version or "?")
        else:
            old_label = "Local: {0}".format(local_version or "?")
            new_label = "GitHub: {0}".format(remote_version or "?")

        self["version_info"].setText(
            "OLD settings ({0})    |    NEW settings ({1})    |    Folder: {2}".format(
                old_label, new_label, self.folder
            )
        )

        self["status"].setText("Comparing...")
        report = self.build_report(local_version, remote_version,
                                   local_bouquets, remote_bouquets_raw)
        self.report_text = report
        self["result"].setText(report)

        # --- Auto-save u /tmp ---
        try:
            with open("/tmp/ciefp_comparison.txt", "w", encoding="utf-8") as f:
                f.write(report)
            self["status"].setText("Comparison complete. Saved to /tmp/ciefp_comparison.txt")
        except Exception as e:
            self["status"].setText("Comparison complete. Save failed: " + to_unicode(str(e)))

    # -----------------------------------------------------------------
    def build_report(self, local_version, remote_version, local_bouquets, remote_bouquets_raw):
        lines = []

        local_date = parse_date(local_version)
        remote_date = parse_date(remote_version)

        if local_date and remote_date and local_date >= remote_date:
            old_source = "GitHub"
            new_source = "Local"
            old_version = remote_version
            new_version = local_version
            old_bouquets = remote_bouquets_raw
            new_bouquets = local_bouquets
        else:
            old_source = "Local"
            new_source = "GitHub"
            old_version = local_version
            new_version = remote_version
            old_bouquets = local_bouquets
            new_bouquets = remote_bouquets_raw

        lines.append("OLD settings ({0}): {1}".format(old_source, old_version or "unknown"))
        lines.append("NEW settings ({0}): {1}".format(new_source, new_version or "unknown"))
        lines.append("")
        lines.append("Results:")
        lines.append("=" * 100)

        old_names = set(old_bouquets.keys()) - IGNORED_BOUQUETS
        new_names = set(new_bouquets.keys()) - IGNORED_BOUQUETS

        new_bouquet_files = sorted(new_names - old_names)
        removed_bouquet_files = sorted(old_names - new_names)
        common_bouquets = sorted(old_names & new_names)

        if new_bouquet_files:
            lines.append("")
            lines.append("### NEW BOUQUETS ({0}) ###".format(len(new_bouquet_files)))
            for fn in new_bouquet_files:
                name = self._get_bouquet_name(fn, new_bouquets, new_source)
                lines.append("  + {0}".format(name or fn))

        if removed_bouquet_files:
            lines.append("")
            lines.append("### REMOVED BOUQUETS ({0}) ###".format(len(removed_bouquet_files)))
            for fn in removed_bouquet_files:
                name = self._get_bouquet_name(fn, old_bouquets, old_source)
                lines.append("  - {0}".format(name or fn))

        lines.append("")
        lines.append("### CHANGED BOUQUETS ###")
        changed_count = 0
        # Brojači za summary
        total_added = 0
        total_removed = 0
        total_streamrelay_added = 0
        total_streamrelay_removed = 0
        total_markers_added = 0
        total_markers_removed = 0

        for fn in common_bouquets:
            if old_source == "Local":
                old_services = read_bouquet_services(old_bouquets[fn])
                old_name = read_bouquet_name(old_bouquets[fn])
                old_lamedb = self.local_lamedb
            else:
                old_services = read_bouquet_services_from_text(old_bouquets[fn])
                old_name = read_bouquet_name_from_text(old_bouquets[fn])
                old_lamedb = self.remote_lamedb

            if new_source == "Local":
                new_services = read_bouquet_services(new_bouquets[fn])
                new_name = read_bouquet_name(new_bouquets[fn])
                new_lamedb = self.local_lamedb
            else:
                new_services = read_bouquet_services_from_text(new_bouquets[fn])
                new_name = read_bouquet_name_from_text(new_bouquets[fn])
                new_lamedb = self.remote_lamedb

            added = new_services - old_services
            removed = old_services - new_services
            # Broj u globalne statističke
            total_added += len(added)
            total_removed += len(removed)

            # Klasifikuj po tipu
            for svc in added:
                if svc.startswith("MARKER::"):
                    total_markers_added += 1
                elif "http" in svc.lower() or "4097:" in svc or "5001:" in svc or "5002:" in svc:
                    total_streamrelay_added += 1

            for svc in removed:
                if svc.startswith("MARKER::"):
                    total_markers_removed += 1
                elif "http" in svc.lower() or "4097:" in svc or "5001:" in svc or "5002:" in svc:
                    total_streamrelay_removed += 1
            name_changed = (old_name != new_name)

            if not added and not removed and not name_changed:
                continue

            changed_count += 1
            lines.append("")
            lines.append("{0}".format(new_name or old_name or fn))
            lines.append("  File: {0}".format(fn))

            if name_changed:
                lines.append("  [NAME CHANGED]")
                lines.append("    old: {0}".format(old_name))
                lines.append("    new: {0}".format(new_name))

            if added:
                lines.append("  + {0} new service(s)".format(len(added)))
                for svc in sorted(added)[:MAX_SERVICES_PER_BOUQUET]:
                    lines.append("      {0}".format(service_to_name(svc, new_lamedb)))
                if len(added) > MAX_SERVICES_PER_BOUQUET:
                    lines.append("      ... and {0} more".format(len(added) - MAX_SERVICES_PER_BOUQUET))

            if removed:
                lines.append("  - {0} removed service(s)".format(len(removed)))
                for svc in sorted(removed)[:MAX_SERVICES_PER_BOUQUET]:
                    lines.append("      {0}".format(service_to_name(svc, old_lamedb)))
                if len(removed) > MAX_SERVICES_PER_BOUQUET:
                    lines.append("      ... and {0} more".format(len(removed) - MAX_SERVICES_PER_BOUQUET))

        if changed_count == 0 and not new_bouquet_files and not removed_bouquet_files:
            lines.append("")
            lines.append("  No changes detected.")
        else:
            lines.append("")
            lines.append("=" * 100)
            lines.append("SUMMARY")
            lines.append("=" * 100)
            lines.append("  Bouquets:  {0} new  |  {1} removed  |  {2} changed".format(
                len(new_bouquet_files), len(removed_bouquet_files), changed_count))
            lines.append("  Channels:  +{0} added  |  -{1} removed".format(
                total_added, total_removed))

            if total_streamrelay_added or total_streamrelay_removed:
                lines.append("    ↳ StreamRelay: +{0}  |  -{1}".format(
                    total_streamrelay_added, total_streamrelay_removed))

            if total_markers_added or total_markers_removed:
                lines.append("    ↳ Markers:     +{0}  |  -{1}".format(
                    total_markers_added, total_markers_removed))

        return "\n".join(lines)

    # -----------------------------------------------------------------
    def _get_bouquet_name(self, filename, bouquets, source):
        if source == "Local":
            return read_bouquet_name(bouquets[filename])
        else:
            return read_bouquet_name_from_text(bouquets[filename])

    # -----------------------------------------------------------------
    def save_report(self):
        if not self.report_text:
            return
        path = "/tmp/ciefp_comparison.txt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.report_text)
            self.session.open(MessageBox,
                              "Report saved to:\n{0}".format(path),
                              MessageBox.TYPE_INFO, timeout=5)
        except Exception as e:
            self.session.open(MessageBox, "Save failed: " + to_unicode(str(e)),
                              MessageBox.TYPE_ERROR, timeout=5)