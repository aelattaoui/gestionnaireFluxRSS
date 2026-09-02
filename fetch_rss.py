import json
import os
import xml.etree.ElementTree as ET
import feedparser
import requests

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
SEEN_FILE = "seen_articles.json"


def load_seen():
  if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
      return set(json.load(f))
  return set()


def save_seen(seen):
  with open(SEEN_FILE, "w", encoding="utf-8") as f:
    json.dump(list(seen), f, indent=2)


def get_feeds_from_opml(opml_path):
  tree = ET.parse(opml_path)
  root = tree.getroot()
  feeds = []
  for outline in root.findall(".//outline[@xmlUrl]"):
    title = outline.attrib.get("title") or outline.attrib.get("text")
    xml_url = outline.attrib.get("xmlUrl")
    if xml_url:
      feeds.append((title, xml_url))
  return feeds


def main():
  if not WEBHOOK_URL:
    print("Erreur: DISCORD_WEBHOOK_URL manquante.")
    return

  seen = load_seen()
  feeds = get_feeds_from_opml("subscriptions.xml")

  for feed_title, feed_url in feeds:
    parsed = feedparser.parse(feed_url)
    # Traiter du plus ancien au plus récent
    for entry in reversed(parsed.entries[:5]):
      entry_id = entry.get("id") or entry.get("link")
      if entry_id in seen:
        continue

      title = entry.get("title", "Sans titre")
      link = entry.get("link", "")

      # Envoi de l'embed sur Discord
      payload = {
          "embeds": [{
              "title": title[:256],
              "url": link,
              "color": 0x5865F2,  # Bleu Discord
              "footer": {"text": f"Source : {feed_title}"},
          }]
      }

      res = requests.post(WEBHOOK_URL, json=payload)
      if res.status_code in (200, 204):
        seen.add(entry_id)
        print(f"Envoyé : {title}")
      else:
        print(f"Échec ({res.status_code}) pour : {title}")

  save_seen(seen)


if __name__ == "__main__":
  main()