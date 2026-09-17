import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Language = "en" | "de";

const translations: Record<Language, Record<string, string>> = {
  en: {},
  de: {
    "Dashboard": "Dashboard",
    "Devices": "Geräte",
    "Events": "Ereignisse",
    "Reports": "Berichte",
    "Settings": "Einstellungen",
    "Historical Data": "Historische Daten",
    "Help & Support": "Hilfe & Support",
    "About": "Über",
    "Expand navigation": "Navigation erweitern",
    "Collapse navigation": "Navigation einklappen",
    "Operations dashboard": "Betriebsübersicht",
    "Last updated": "Zuletzt aktualisiert",
    "Refresh": "Aktualisieren",
    "Refreshing...": "Wird aktualisiert...",
    "Current status, state cache, and device controls in one place.": "Aktueller Status, Zustandsdaten und Gerätesteuerung an einem Ort.",
    "Total devices": "Geräte gesamt",
    "Online": "Online",
    "With alarm": "Mit Alarm",
    "Offline": "Offline",
    "configured appliances": "konfigurierte Geräte",
    "Device card view": "Geräteansicht",
    "Expanded": "Erweitert",
    "Minimal": "Kompakt",
    "Recent events": "Letzte Ereignisse",
    "View all": "Alle anzeigen",
    "entries": "Einträge",
    "Temperature overview": "Temperaturübersicht",
    "Current vs target": "Aktuell vs. Sollwert",
    "Device": "Gerät",
    "Zone": "Zone",
    "Zones": "Zonen",
    "Current": "Aktuell",
    "Target": "Sollwert",
    "Status": "Status",
    "ok": "OK",
    "alarm": "Alarm",
    "offline": "Offline",
    "stale": "Veraltet",
    "Alerts": "Alarme",
    "tracked conditions": "überwachte Bedingungen",
    "No alerts to display": "Keine Alarme vorhanden",
    "No conditions are currently tracked. Check device status for data availability.": "Derzeit werden keine Bedingungen überwacht. Prüfen Sie den Gerätestatus.",
    "Successful": "Erfolgreich",
    "Failed": "Fehlgeschlagen",
    "Pending": "Ausstehend",
    "Active": "Aktiv",
    "Recovering": "Wird wiederhergestellt",
    "Resolved": "Behoben",
    "Automatic refresh": "Automatische Aktualisierung",
    "System activity": "Systemaktivität",
    "Device refresh failed": "Geräteaktualisierung fehlgeschlagen",
    "Device added": "Gerät hinzugefügt",
    "Device updated": "Gerät aktualisiert",
    "Device removed": "Gerät entfernt",
    "Language": "Sprache",
    "English": "Englisch",
    "German": "Deutsch",
    "English (US)": "Englisch (USA)",
    "German (DE)": "Deutsch (DE)",
    "Not updated": "Nicht aktualisiert",
    "No location": "Kein Standort",
    "Open": "Offen",
    "Closed": "Geschlossen",
    "Alarms": "Alarme",
    "None": "Keine",
    "Updated": "Aktualisiert",
    "Status unavailable": "Status nicht verfügbar",
    "Checking status": "Status wird geprüft",
    "Read-only enabled": "Nur-Lesen aktiviert",
    "Controls enabled": "Steuerung aktiviert",
    "Good afternoon!": "Guten Tag!",
    "Good evening": "Guten Abend",
    "Good evening!": "Guten Abend!",
    "Read-only monitoring mode is active. Fridge controls are disabled.": "Der Nur-Lesen-Überwachungsmodus ist aktiv. Die Kühlschranksteuerung ist deaktiviert.",
    "Device state refreshed": "Gerätezustand aktualisiert",
    "Add appliance": "Gerät hinzufügen",
    "Configured appliances": "Konfigurierte Geräte",
    "Search devices...": "Geräte suchen...",
    "Add and discover": "Hinzufügen und erkennen",
    "Connect appliances, inspect their discovered zones, and manage their current-state cache.": "Geräte verbinden, erkannte Zonen prüfen und den aktuellen Zustand verwalten.",
    "Last successful update:": "Letzte erfolgreiche Aktualisierung:",
    "Door": "Tür",
    "Discovery runs immediately": "Die Erkennung startet sofort",
    "Name": "Name",
    "Location": "Standort",
    "Local API URL": "Lokale API-URL",
    "API token": "API-Token",
    "No location configured": "Kein Standort konfiguriert",
    "All devices": "Alle Geräte",
    "Refresh appliance": "Gerät aktualisieren",
    "Finding image...": "Bild wird gesucht...",
    "Image loaded": "Bild geladen",
    "Find fridge image": "Kühlschrankbild suchen",
    "Remove": "Entfernen",
    "Never": "Nie",
    "on": "ein",
    "off": "aus",
    "Temperature setpoint": "Temperatur-Sollwert",
    "Apply setpoint": "Sollwert anwenden",
    "Applying...": "Wird angewendet...",
    "Supported controls": "Unterstützte Steuerungen",
    "Visible but disabled in read-only mode": "Sichtbar, aber im Nur-Lesen-Modus deaktiviert",
    "Only discovered capabilities are actionable": "Nur erkannte Funktionen können verwendet werden",
    "Connection settings": "Verbindungseinstellungen",
    "Technical API state": "Technischer API-Zustand",
    "Read-only view of the latest reported values": "Nur-Lesen-Ansicht der zuletzt gemeldeten Werte",
    "Historical reporting remains connected to the existing InfluxDB and Grafana stack.": "Die historische Berichterstattung bleibt mit dem bestehenden InfluxDB- und Grafana-System verbunden.",
    "Historical reporting": "Historische Berichterstattung",
    "TempVerity does not duplicate the existing historical telemetry pipeline. InfluxDB and Grafana remain independent so monitoring continues even when either service is unavailable.": "TempVerity dupliziert die bestehende Pipeline für historische Telemetriedaten nicht. InfluxDB und Grafana bleiben unabhängig, damit die Überwachung auch bei Ausfall eines Dienstes fortgesetzt wird.",
    "Set TEMPVERITY_GRAFANA_URL to show the Grafana reports link here.": "Setzen Sie TEMPVERITY_GRAFANA_URL, um hier den Link zu den Grafana-Berichten anzuzeigen.",
    "Current state": "Aktueller Zustand",
    "Alarm history": "Alarmverlauf",
    "Current and historical appliance conditions, including grace-period state.": "Aktuelle und historische Gerätezustände einschließlich des Status der Karenzzeit.",
    "Read-only operational and audit feed for TempVerity.": "Nur-Lesen-Betriebs- und Prüfprotokoll für TempVerity.",
    "Purge events": "Ereignisse löschen",
    "External": "Extern",
    "Open Grafana reports": "Grafana-Berichte öffnen",
    "Current-state snapshot": "Momentaufnahme des aktuellen Zustands",
    "Show": "Anzeigen",
    "Hide": "Ausblenden",
    "Save connection": "Verbindung speichern",
    "Good afternoon": "Guten Tag",
    "Loading...": "Wird geladen...",
    "Loading devices...": "Geräte werden geladen...",
    "Unable to load devices.": "Geräte konnten nicht geladen werden.",
    "Discovering...": "Erkennung läuft...",
    "zone": "Zone",
    "zones": "Zonen",
    "Uses the SMTP sender configured in Settings": "Verwendet den in den Einstellungen konfigurierten SMTP-Absender",
    "Disabled": "Deaktiviert",
    "Enabled": "Aktiviert",
    "Export frequency": "Exporthäufigkeit",
    "Daily": "Täglich",
    "Weekly": "Wöchentlich",
    "Monthly": "Monatlich",
    "Quarterly": "Vierteljährlich",
    "Yearly": "Jährlich",
    "All": "Alle",
    "Target email address(es)": "Ziel-E-Mail-Adresse(n)",
    "Save report settings": "Berichtseinstellungen speichern",
    "InfluxDB history": "InfluxDB-Verlauf",
    "InfluxDB connection from environment": "InfluxDB-Verbindung aus der Umgebung",
    "Missing Config": "Konfiguration fehlt",
    "Write interval minutes": "Schreibintervall in Minuten",
    "InfluxDB connection details are incomplete": "Die InfluxDB-Verbindungsdaten sind unvollständig",
    "Last successful write: None recorded": "Letzter erfolgreicher Schreibvorgang: Keine Aufzeichnung",
    "Save historical data settings": "Einstellungen für historische Daten speichern",
    "Long-term temperature and appliance-state storage for Grafana and reporting. Connection details are provided by Docker Compose environment variables.": "Langfristige Speicherung von Temperaturen und Gerätezuständen für Grafana und Berichte. Verbindungsdaten werden über Docker-Compose-Umgebungsvariablen bereitgestellt.",
    "Loading current state...": "Aktueller Zustand wird geladen...",
    "Application information, features, and how it works.": "Anwendungsinformationen, Funktionen und Arbeitsweise.",
    "What TempVerity does": "Was TempVerity macht",
    "How it works": "So funktioniert es",
    "Historical data": "Historische Daten",
    "Email reports": "E-Mail-Berichte",
    "Alerts and notifications": "Alarme und Benachrichtigungen",
    "Safety mode": "Sicherheitsmodus",
    "Version": "Version",
    "Application behavior and notification configuration. Changes here do not alter appliance parameters.": "Anwendungsverhalten und Benachrichtigungskonfiguration. Änderungen hier verändern keine Geräteparameter.",
    "Monitoring": "Überwachung",
    "SMTP notifications": "SMTP-Benachrichtigungen",
    "No test sent": "Kein Test gesendet",
    "Host": "Host",
    "Security": "Sicherheit",
    "Sender username": "Absender-Benutzername",
    "Sender password": "Absender-Passwort",
    "Sender address": "Absenderadresse",
    "Recipients": "Empfänger",
    "Save SMTP settings": "SMTP-Einstellungen speichern",
    "Send test email": "Test-E-Mail senden",
    "Alert timing and rules": "Alarmzeiten und Regeln",
    "Grace periods and software-defined limits": "Karenzzeiten und softwaredefinierte Grenzwerte",
    "Connectivity grace minutes": "Karenzzeit bei Verbindungsfehlern in Minuten",
    "Alarm grace minutes": "Alarm-Karenzzeit in Minuten",
    "Recovery grace minutes": "Karenzzeit für Wiederherstellung in Minuten",
    "Recovery notifications": "Wiederherstellungsbenachrichtigungen",
    "Repeat notifications": "Wiederholte Benachrichtigungen",
    "Alarm rule helper": "Assistent für Alarmregeln",
    "Add recommended rules": "Empfohlene Regeln hinzufügen",
    "Select device": "Gerät auswählen",
    "Temperature above": "Temperatur über",
    "Temperature below": "Temperatur unter",
    "Door remains open": "Tür bleibt offen",
    "Threshold (°C)": "Grenzwert (°C)",
    "Grace period (min)": "Karenzzeit (Min.)",
    "Recovery grace (min)": "Wiederherstellungskarenz (Min.)",
    "Add alarm rule": "Alarmregel hinzufügen",
    "Save alert settings": "Alarmeinstellungen speichern",
    "Login access": "Anmeldezugang",
    "Optional administrator and viewer access": "Optionaler Administrator- und Nur-Lesen-Zugang",
    "Enable login": "Anmeldung aktivieren",
    "Require login for dashboard": "Anmeldung für Dashboard erforderlich",
    "Session duration": "Sitzungsdauer",
    "Duration unit": "Dauer-Einheit",
    "Administrator password": "Administrator-Passwort",
    "View-only password": "Nur-Lesen-Passwort",
    "Save login settings": "Anmeldeeinstellungen speichern",
    "Software alarm rules (JSON)": "Software-Alarmregeln (JSON)",
    "Advanced rule configuration": "Erweiterte Regelkonfiguration",
    "Hours": "Stunden",
    "Days": "Tage",
    "Months": "Monate",
    "STARTTLS": "STARTTLS",
    "TLS": "TLS",
    "Leave blank to keep current password": "Leer lassen, um das aktuelle Passwort beizubehalten",
    "Saving...": "Wird gespeichert...",
    "Sending test...": "Test wird gesendet...",
    "Checking historical data status...": "Status der historischen Daten wird geprüft...",
    "disabled": "deaktiviert",
    "enabled": "aktiviert",
    "history required": "Verlauf erforderlich",
    "Checking monitoring mode...": "Überwachungsmodus wird geprüft...",
    "Polling runs independently for each configured device and uses the interval stored on that device.": "Die Abfrage läuft für jedes konfigurierte Gerät unabhängig und verwendet das für dieses Gerät gespeicherte Intervall.",
    "When login is enabled, all application pages require a password. The view-only account can see monitoring, alarms, events, and reports, but not Devices or Settings.": "Wenn die Anmeldung aktiviert ist, benötigen alle Anwendungsseiten ein Passwort. Das Nur-Lesen-Konto kann Überwachung, Alarme, Ereignisse und Berichte sehen, aber nicht Geräte oder Einstellungen.",
    "Event feed": "Ereignisprotokoll",
    "Showing the 25 most recent entries": "Die 25 neuesten Einträge werden angezeigt",
    "TIME": "ZEIT",
    "EVENT": "EREIGNIS",
    "Temperature limits": "Temperaturgrenzen",
    "Setpoint range:": "Sollwertbereich:",
    "to": "bis",
    "Upper alarm limit:": "Obere Alarmgrenze:",
    "Lower alarm limit:": "Untere Alarmgrenze:",
    "Alarm refresh interval:": "Alarm-Aktualisierungsintervall:",
    "Alarm limits are reported by the appliance. The available API does not provide an endpoint to change them.": "Die Alarmgrenzen werden vom Gerät gemeldet. Die verfügbare API bietet keinen Endpunkt, um sie zu ändern.",
    "Safety parameters": "Sicherheitsparameter",
    "Power-failure upper threshold:": "Oberer Schwellenwert bei Stromausfall:",
    "Power-failure lower threshold:": "Unterer Schwellenwert bei Stromausfall:",
    "Emergency alarm:": "Notfallalarm:",
    "Manual defrost:": "Manuelles Abtauen:",
    "Normal": "Normal",
    "Inactive": "Inaktiv",
    "Temperature alarm refresh time": "Aktualisierungsintervall des Temperaturalarmes",
    "Change the temperature alarm refresh time to": "Temperaturalarm-Aktualisierungsintervall ändern auf",
    "Apply alarm timing": "Alarmzeit anwenden",
    "min": "Min.",
    "minutes?": "Minuten?",
    "Checking": "Wird geprüft",
    "checking": "wird geprüft",
    "Temperature unit": "Temperatureinheit",
    "Acoustic alarm": "Akustischer Alarm",
    "Presentation light": "Präsentationslicht",
    "Child lock": "Kindersicherung",
    "Eco mode": "Eco-Modus",
    "Refrigerator": "Kühlschrank",
    "Freezer": "Gefrierschrank",
    "Change endpoint, token, or operator label": "Endpunkt, Token oder Bedienerbezeichnung ändern",
    "Loading cached state...": "Zwischengespeicherter Zustand wird geladen...",
    "setpoint": "Sollwert",
    "open": "offen",
    "closed": "geschlossen",
    "Cooling": "Kühlung",
    "Open door lock": "Türsperre öffnen",
    "Acknowledge door alarm": "Türalarm quittieren",
    "Acknowledge door-lock alarm": "Türsperrenalarm quittieren",
    "Acknowledge emergency alarm": "Notfallalarm quittieren",
    "Acknowledge upper power alarm": "Oberen Stromausfallalarm quittieren",
    "Acknowledge lower power alarm": "Unteren Stromausfallalarm quittieren",
    "Acknowledge upper temperature alarm": "Oberen Temperaturalarm quittieren",
    "Acknowledge lower temperature alarm": "Unteren Temperaturalarm quittieren",
    "TempVerity is a self-hosted temperature monitoring application for professional refrigeration appliances in laboratories, pharmacies, healthcare facilities, and similar environments.": "TempVerity ist eine selbst gehostete Temperaturüberwachungsanwendung für professionelle Kühlgeräte in Laboren, Apotheken, Gesundheitseinrichtungen und ähnlichen Bereichen.",
    "It brings device status, current and target temperatures, door conditions, alarms, and operational events into one interface, helping you identify conditions that need attention.": "Sie bündelt Gerätestatus, aktuelle und Solltemperaturen, Türzustände, Alarme und Betriebsereignisse in einer Oberfläche und hilft dabei, kritische Zustände zu erkennen.",
    "TempVerity polls each configured appliance through its local API, stores the latest reported state locally, and evaluates available readings against configured software alarm rules. Update frequency depends on the polling interval and device connectivity.": "TempVerity fragt jedes konfigurierte Gerät über dessen lokale API ab, speichert den zuletzt gemeldeten Zustand lokal und bewertet verfügbare Messwerte anhand konfigurierter Software-Alarmregeln. Die Aktualisierungshäufigkeit hängt vom Abfrageintervall und der Geräteverbindung ab.",
    "Current-state monitoring, historical storage, reporting, and alert delivery can be configured independently so routine visibility and long-term records can use different intervals.": "Die Überwachung des aktuellen Zustands, historische Speicherung, Berichte und Alarmzustellung können unabhängig voneinander konfiguriert werden.",
    "TempVerity can write long-term appliance samples to a dedicated InfluxDB bucket while keeping application state in its local database. Historical writes use their own interval and store one sample per reported device zone.": "TempVerity kann langfristige Gerätedaten in einen eigenen InfluxDB-Bucket schreiben und den Anwendungszustand in der lokalen Datenbank halten. Historische Schreibvorgänge verwenden ein eigenes Intervall und speichern einen Messwert pro gemeldeter Gerätezone.",
    "Grafana dashboard links can be added on the Historical Data page. Embedded dashboard cards are loaded only when that page is opened and can be hidden entirely through the deployment environment.": "Grafana-Dashboard-Links können auf der Seite Historische Daten hinzugefügt werden. Eingebettete Dashboard-Karten werden nur beim Öffnen dieser Seite geladen und können über die Deployment-Umgebung vollständig ausgeblendet werden.",
    "Scheduled historical reports can be generated from InfluxDB data and delivered as email attachments. Reports include CSV data and a PDF summary with temperature trends.": "Geplante historische Berichte können aus InfluxDB-Daten erstellt und als E-Mail-Anhänge versendet werden. Die Berichte enthalten CSV-Daten und eine PDF-Zusammenfassung mit Temperaturverläufen.",
    "Report frequency and recipients are configured on the Historical Data page. Sender address, SMTP host, credentials, and transport security are reused from the SMTP notification settings.": "Berichtshäufigkeit und Empfänger werden auf der Seite Historische Daten konfiguriert. Absenderadresse, SMTP-Host, Zugangsdaten und Transportsicherheit werden aus den SMTP-Benachrichtigungseinstellungen übernommen.",
    "TempVerity tracks connectivity problems, appliance-reported alarms, and configured software alarm conditions. Grace periods let you control how long a condition must persist before a notification is sent.": "TempVerity überwacht Verbindungsprobleme, von Geräten gemeldete Alarme und konfigurierte Software-Alarmbedingungen. Karenzzeiten legen fest, wie lange eine Bedingung bestehen muss, bevor eine Benachrichtigung versendet wird.",
    "Alerts appear in the application and can be delivered by email when SMTP is configured and enabled. Recovery and repeat notifications follow your settings. Recorded alarms and events are available for review in their dedicated pages.": "Alarme werden in der Anwendung angezeigt und können bei konfiguriertem und aktiviertem SMTP per E-Mail zugestellt werden. Wiederherstellungs- und Wiederholungsbenachrichtigungen folgen Ihren Einstellungen.",
    "The current operating mode could not be retrieved. Check the application connection before relying on the status shown here.": "Der aktuelle Betriebsmodus konnte nicht abgerufen werden. Prüfen Sie die Anwendungsverbindung, bevor Sie sich auf den angezeigten Status verlassen.",
    "Checking whether this installation allows appliance control actions.": "Es wird geprüft, ob diese Installation Steuerungsaktionen für Geräte erlaubt.",
    "Read-only monitoring mode is enabled. Appliance control actions are disabled, while monitoring and alerts remain available.": "Der Nur-Lesen-Überwachungsmodus ist aktiviert. Gerätesteuerungen sind deaktiviert, während Überwachung und Alarme verfügbar bleiben.",
    "Read-only monitoring mode is disabled. Authorized users can send supported control actions to connected appliances.": "Der Nur-Lesen-Überwachungsmodus ist deaktiviert. Berechtigte Benutzer können unterstützte Steuerungsaktionen an verbundene Geräte senden.",
    "TempVerity supports operational awareness; it does not guarantee storage conditions, certify regulatory compliance, or replace appliance safety systems and established monitoring procedures.": "TempVerity unterstützt die betriebliche Übersicht, garantiert jedoch keine Lagerbedingungen, bestätigt keine gesetzliche Konformität und ersetzt weder Sicherheitssysteme der Geräte noch etablierte Überwachungsverfahren.",
  },
};

const originalText = new WeakMap<Text, string>();
const translatedText = new WeakMap<Text, string>();
const originalAttributes = new WeakMap<Element, Map<string, string>>();
const translatedAttributes = new WeakMap<Element, Map<string, string>>();

function translateRenderedTree(language: Language) {
  const germanToEnglish = new Map(Object.entries(translations.de).map(([english, german]) => [german, english]));
  const translate = (value: string) => {
    const source = language === "de" ? (germanToEnglish.get(value.trim()) ?? value.trim()) : value.trim();
    return translations[language][source] ?? source;
  };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node: Node | null;
  while ((node = walker.nextNode())) {
    const text = node as Text;
    const previousTranslation = translatedText.get(text);
    if (!originalText.has(text) || (previousTranslation !== undefined && previousTranslation !== text.data)) {
      originalText.set(text, germanToEnglish.get(text.data.trim()) ?? text.data);
    }
    const source = originalText.get(text) ?? text.data;
    const translated = translate(source);
    const nextText = `${source.match(/^\s*/)?.[0] ?? ""}${translated}${source.match(/\s*$/)?.[0] ?? ""}`;
    if (text.data !== nextText) text.data = nextText;
    translatedText.set(text, nextText);
  }
  document.querySelectorAll<HTMLElement>("[title], [aria-label], input[placeholder], textarea[placeholder]").forEach((element) => {
    const attributes = originalAttributes.get(element) ?? new Map<string, string>();
    for (const name of ["title", "aria-label", "placeholder"]) {
      const current = element.getAttribute(name);
      if (current === null) continue;
      const previousTranslation = translatedAttributes.get(element)?.get(name);
      if (!attributes.has(name) || (previousTranslation !== undefined && previousTranslation !== current)) attributes.set(name, germanToEnglish.get(current) ?? current);
      const nextValue = translate(attributes.get(name) ?? current);
      if (current !== nextValue) element.setAttribute(name, nextValue);
      const nextTranslations = translatedAttributes.get(element) ?? new Map<string, string>();
      nextTranslations.set(name, nextValue);
      translatedAttributes.set(element, nextTranslations);
    }
    originalAttributes.set(element, attributes);
  });
}

function detectLanguage(): Language {
  if (typeof navigator === "undefined") return "en";
  return navigator.language.toLowerCase().startsWith("de") ? "de" : "en";
}

const LanguageContext = createContext<{ language: Language; setLanguage: (language: Language) => void; t: (text: string) => string } | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = window.localStorage.getItem("tempverity-language");
    return saved === "de" || saved === "en" ? saved : detectLanguage();
  });
  const setLanguage = (next: Language) => {
    setLanguageState(next);
    window.localStorage.setItem("tempverity-language", next);
  };
  useEffect(() => {
    document.documentElement.lang = language;
    translateRenderedTree(language);
    const observer = new MutationObserver(() => translateRenderedTree(language));
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    return () => observer.disconnect();
  }, [language]);
  const t = (text: string) => translations[language][text] ?? text;
  return <LanguageContext.Provider value={{ language, setLanguage, t }}>{children}</LanguageContext.Provider>;
}

export function useTranslation() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error("useTranslation must be used inside LanguageProvider");
  return context;
}
