import os
import json
import xml.etree.ElementTree as ET
import feedparser
import requests
from google import genai

SEEN_FILE = "seen_articles.json"

# Configuration des thèmes (Fichier XML -> Variable Webhook Discord)
THEMES_CONFIG = {
    "subBigData.xml": "DISCORD_WEBHOOK_BIGDATA",
    "subCybersecurite.xml": "DISCORD_WEBHOOK_CYBERSECURITE",
    "subDeveloppement.xml": "DISCORD_WEBHOOK_DEVELOPPEMENT",
    "subManagementEtStrategie.xml": "DISCORD_WEBHOOK_MANAGEMENT",
    "subMobilite.xml": "DISCORD_WEBHOOK_MOBILITE",
    "subOptimisationSI.xml": "DISCORD_WEBHOOK_OPTIMISATION_SI",
    "subSIEtEnvironnement.xml": "DISCORD_WEBHOOK_SI_ENVIRONNEMENT",
    "subIA.xml": "DISCORD_WEBHOOK_IA",
    "subBlockchain.xml": "DISCORD_WEBHOOK_BLOCKCHAIN",
}

# Initialisation sécurisée du client Gemini
gemini_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_key) if gemini_key else None


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except (json.JSONDecodeError, ValueError):
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(seen)), f, indent=2, ensure_ascii=False)


def extract_rss_urls(opml_file):
    urls = []
    if not os.path.exists(opml_file):
        return urls
    try:
        tree = ET.parse(opml_file)
        root = tree.getroot()
        for elem in root.iter("outline"):
            xml_url = elem.attrib.get("xmlUrl")
            if xml_url:
                urls.append(xml_url)
    except Exception as e:
        print(f"Erreur de lecture de {opml_file} : {e}")
    return urls


def generer_synthese_theme(theme_name, articles):
    if not client or not articles:
        return None

    texte_articles = ""
    for idx, a in enumerate(articles, 1):
        texte_articles += f"{idx}. Titre : {a['title']}\n   Résumé : {a.get('summary', 'Pas de description')}\n\n"

    prompt = f"""
Tu es un expert en veille technologique pour le domaine '{theme_name}'.
Voici la liste des nouveaux articles parus :

{texte_articles}

Rédige une synthèse globale et concise en français sous forme de 3 à 5 puces clés (bullet points).
Mets en valeur les tendances marquantes ou les annonces majeures.
Sois direct et professionnel. N'ajoute pas d'introduction ni de conclusion, donne directement les puces.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"Erreur lors de la génération Gemini pour {theme_name} : {e}")
        return None


def envoyer_article_discord(webhook_url, entry):
    payload = {"content": f"**{entry.title}**\n{entry.link}"}
    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Erreur d'envoi Discord : {e}")


def envoyer_synthese_discord(webhook_url, theme_name, synthese_text):
    if not webhook_url or not synthese_text:
        return

    payload = {
        "embeds": [
            {
                "title": f"📊 Synthèse flash — {theme_name}",
                "description": synthese_text,
                "color": 3447003,
                "footer": {"text": "Généré automatiquement par Gemini 2.5 Flash"}
            }
        ]
    }
    try:
        requests.post(webhook_url, json=payload)
    except Exception as e:
        print(f"Erreur d'envoi de la synthèse Discord : {e}")


def main():
    seen = load_seen()
    is_first_run = len(seen) == 0  # Sécurité pour le premier lancement

    for opml_file, webhook_env_var in THEMES_CONFIG.items():
        webhook_url = os.environ.get(webhook_env_var)
        if not webhook_url:
            continue

        theme_name = opml_file.replace("sub", "").replace(".xml", "")
        rss_urls = extract_rss_urls(opml_file)
        nouveaux_articles_du_theme = []

        for url in rss_urls:
            feed = feedparser.parse(url)
            # On limite aux 5 plus récents par flux
            entries = feed.entries[:5] if is_first_run else feed.entries

            for entry in entries:
                article_id = entry.get("id", entry.get("link"))
                if not article_id or article_id in seen:
                    continue

                # 1. Envoi du lien brut sur Discord
                envoyer_article_discord(webhook_url, entry)

                # 2. Ajout à la liste mémoire + préparation de la synthèse
                seen.add(article_id)
                nouveaux_articles_du_theme.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", entry.get("description", ""))
                })

        # 3. Génération de la synthèse si on a au moins 2 nouveaux articles dans ce thème
        if len(nouveaux_articles_du_theme) >= 2 and not is_first_run:
            print(f"Génération de la synthèse pour le thème {theme_name} ({len(nouveaux_articles_du_theme)} articles)...")
            synthese = generer_synthese_theme(theme_name, nouveaux_articles_du_theme)
            if synthese:
                envoyer_synthese_discord(webhook_url, theme_name, synthese)

    save_seen(seen)


if __name__ == "__main__":
    main()
