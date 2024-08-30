import time
import json
import logging
from datetime import datetime
import anthropic
from wg_gesucht_client import WgGesuchtClient

CLAUDE_API_KEY = "your-api-key"
client = anthropic.Client(api_key=CLAUDE_API_KEY)
city = 'Your City'

# Ihre persönlichen Informationen
your_info = """
Infos about yourself, so the message is more personal
"""

# Konfiguration des Loggings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("wg_gesucht_bot.log"),
        logging.StreamHandler()
    ]
)

def load_contacted_offers():
    try:
        with open("contacted_offers.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_contacted_offer(offer_id, title, url, timestamp):
    contacted_offers = load_contacted_offers()
    contacted_offers.append({
        "offer_id": offer_id,
        "title": title,
        "url": url,
        "timestamp": timestamp
    })
    with open("contacted_offers.json", "w") as file:
        json.dump(contacted_offers, file, indent=2)

def is_offer_contacted(offer_id):
    contacted_offers = load_contacted_offers()
    return any(offer["offer_id"] == offer_id for offer in contacted_offers)

def generate_message_with_ai(offer_description, your_info):
    #German prompt for creating the message
    prompt = f"""
    Du bist ein 19-jähriger Student, der eine Nachricht für eine WG-Bewerbung auf WG-Gesucht schreibt. Deine Aufgabe ist es, eine lockere, authentische Nachricht zu verfassen, die zu deiner Persönlichkeit passt und gleichzeitig das Interesse der potenziellen Mitbewohner weckt.

    WG-Anzeige:
    {offer_description}

    Deine Infos:
    {your_info}

    Schreibe eine Nachricht und beachte dabei:

    1. Beginne direkt und locker, ohne formelle Anrede oder Bewerbungsfloskeln. Stelle dich kurz vor (Name, Alter, Studium).
    2. Erzähle etwas über deine Hobbys, Interessen und Erfahrungen, die dich als interessanten Mitbewohner auszeichnen.
    3. Sei authentisch und natürlich, als würdest du mit Freunden schreiben. Vermeide jegliche formelle Sprache.
    4. Halte die Nachricht kurz und prägnant (max. 1200 Zeichen).
    5. Erwähne 1-2 Dinge, auf die du dich in der WG freuen würdest oder stelle eine konkrete Frage zur WG.
    6. Schließe locker ab, ohne förmliche Grußformeln.

    Wichtig:
    - Keine Sätze wie "Ich bewerbe mich hiermit..." oder "Ich freue mich, mich vorzustellen..."
    - Keine förmlichen Anreden oder Grußformeln
    - Keine allgemeinen Aussagen über WGs oder Wohnungssuche
    - Schreibe, als würdest du eine Nachricht an potenzielle neue Freunde schreiben

    Die Nachricht sollte sich natürlich und ungezwungen lesen, als käme sie wirklich von einem 19-jährigen Studenten. Konzentriere dich darauf, deine Persönlichkeit und dein Interesse an der WG-Gemeinschaft zu vermitteln, anstatt zu sehr auf die Details der Anzeige einzugehen.
    """

    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=2000,
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text.strip()




def automated_wg_search():
    client = WgGesuchtClient()
    
    logging.info("Starting automated WG search")
    
    if not client.login("E-Mail", "Passwort"):
        logging.error("Login failed. Aborting.")
        return

    cities = client.findCity(city)
    if not cities:
        logging.error("Couldn't find Your City. Aborting.")
        return

    city_id = cities[0]['city_id']
    logging.info(f"Found {city} with city ID: {city_id}")

    while True:
        try:
            logging.info("Starting new search cycle")
            
            offers = client.offers(city_id, '0', '450', '12', 5)  # WG-Zimmer, max 500€, min 20m², max 5er WG
            if not offers:
                logging.info("No offers found in this cycle")
            else:
                logging.info(f"Found {len(offers)} offers")
                for offer in offers:
                    offer_id = offer['offer_id']
                    if not is_offer_contacted(offer_id):
                        logging.info(f"Processing new offer: {offer_id}")
                        offer_detail = client.offerDetail(offer_id)
                        if offer_detail:
                            description = offer_detail.get('freetext_property_description', '')
                            description += offer_detail.get('freetext_area_description', '')
                            description += offer_detail.get('freetext_flatshare', '' )
                            description += offer_detail.get('freetext_other', '')
                            ai_response = generate_message_with_ai(description, your_info)
                            
                            logging.info(f"Generated message for offer {offer_id}:")
                            logging.info(f"Personalized message: {ai_response}")
                            
                            if client.contactOffer(offer_id, ai_response):
                                logging.info(f"Successfully contacted offer {offer_id}")
                                save_contacted_offer(offer_id, offer_detail.get('offer_title', ''), offer_detail.get('url', ''), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                            else:
                                logging.warning(f"Failed to contact offer {offer_id}")
                    else:
                        logging.info(f"Offer {offer_id} already contacted, skipping")

            logging.info("Search cycle completed. Waiting for 5 minutes before next cycle.")
            time.sleep(300)  # 5 Minuten warten
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            logging.info("Waiting for 5 minutes before retrying.")
            time.sleep(300)  # Warte auch bei Fehlern, um die API nicht zu überlasten

if __name__ == "__main__":
    automated_wg_search()