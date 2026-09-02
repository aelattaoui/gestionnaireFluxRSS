import json
import os
import xml.etree.ElementTree as ET
import feedparser
import requests

SEEN_FILE = "seen_articles.json"

# Mappage : Nom du fichier XML -> Nom de la variable Secret GitHub
THEMES_CONFIG = {
    "subBigData.xml": "DISCORD_WEBHOOK_BIGDATA",
    "subCybersecurite.xml": "DISCORD_WEBHOOK_CYBERSECURITE",
    "subDeveloppement.xml": "DISCORD_WEBHOOK_DEVELOPPEMENT",
    "subManagementEtStrategie.xml": "DISCORD_WEBHOOK_MANAGEMENT",
    "subMobilite.xml": "DISCORD_WEBHOOK_MOBILITE",
    "subOptimisationSI.xml": "DISCORD_WEBHOOK_OPTIMISATION_SI",
    "subSIEtEnvironnement.xml": "DISCORD_WEBHOOK_SI_ENVIRONNEMENT",
    "subIA.xml": "DISCORD_WEBHOOK_IA",  # À ajuster selon le nom exact de ton fichier IA,
    "subBlockchain.xml": "DISCORD_WEBHOOK_BLOCKCHAIN"
}


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (json.JSONDecodeError, ValueError):
        # En cas de fichier corrompu, on repart sur un ensemble vide sans crasher
        return set()


def save_seen(seen):
  with open(SEEN_FILE, "w", encoding="utf-8") as f:
    json.dump(list(seen), f, indent=2)


def get_feeds_from_opml(opml_path):
  if not os.path.exists(opml_path):
    return []
  tree = ET.parse(opml_path)
  root = tree.getroot()
  feeds = []
  for outline in root.findall(".//outline[@xmlUrl]"):
    title = outline.attrib.get("title") or outline.attrib.get("text")
    xml_url = outline.attrib.get("xmlUrl")
    if xml_url:
      feeds.append((title, xml_url))
  return feeds


def process_theme(xml_file, env_var, seen):
  webhook_url = os.environ.get(env_var)
  if not webhook_url:
    print(f"Skipped {xml_file}: Secret {env_var} non défini.")
    return

  feeds = get_feeds_from_opml(xml_file)
  if not feeds:
    return

  print(f"--- Traitement de {xml_file} ---")
  for feed_title, feed_url in feeds:
    parsed = feedparser.parse(feed_url)
    for entry in reversed(parsed.entries[:5]):
      entry_id = entry.get("id") or entry.get("link")
      if entry_id in seen:
        continue

      title = entry.get("title", "Sans titre")
      link = entry.get("link", "")

      payload = {
          "embeds": [{
              "title": title[:256],
              "url": link,
              "color": 0x5865F2,
              "footer": {"text": f"Source : {feed_title}"},
          }]
      }

      res = requests.post(webhook_url, json=payload)
      if res.status_code in (200, 204):
        seen.add(entry_id)
        print(f"[{xml_file}] Envoyé : {title}")
      else:
        print(f"[{xml_file}] Échec ({res.status_code}) : {title}")


def main():
  seen = load_seen()

  for xml_file, env_var in THEMES_CONFIG.items():
    process_theme(xml_file, env_var, seen)

  save_seen(seen)


if __name__ == "__main__":
  main()
if __name__ == "__main__":
  main()
