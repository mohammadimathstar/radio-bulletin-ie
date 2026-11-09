import spacy


nlp = spacy.load(
    "nl_core_news_sm",
    disable=["ner", "lemmatizer", "attribute_ruler"],
)

def sentence_spans(text: str) -> list[tuple[int, int]]:
    """
    Return sentence spans as (start, end) character offsets.
    Offsets refer to the original, unchanged text.
    """
    if not text.strip():
        return []

    doc = nlp(text)

    return [
        (sent.start_char, sent.end_char)
        for sent in doc.sents
    ]



def chunk_text(
    text: str,
    max_chars: int,
) -> list[tuple[int, str]]:
    """
    Group complete sentences into chunks.

    Returns:
        [(global_offset, chunk_text), ...]
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")

    spans = sentence_spans(text)

    if not spans:
        return []

    chunks = []
    current_start = spans[0][0]
    current_end = current_start

    for sentence_start, sentence_end in spans:
        proposed_length = sentence_end - current_start

        if (
            current_end > current_start
            and proposed_length > max_chars
        ):
            chunks.append((
                current_start,
                text[current_start:current_end],
            ))

            current_start = sentence_start

        current_end = sentence_end

    if current_end > current_start:
        chunks.append((
            current_start,
            text[current_start:current_end],
        ))

    return chunks


if __name__ == "__main__":
    # Example usage
    example_text = (
        "RADIO 1 van 24 JULI 1939. Goedenavond dames en heeren. Nieuwsberichten van het ANP. Publicatie, in welken vorm ook, is verbodn. Eerste uitz. vvoor de NCRV (2e 10,-) Uit de Staatscourant: Aan den heer .C. VAN BEEK is op zijn verzoek met ingang van 7 AUGUSTUS 1939 eervol ontslag verleend als Burgemeester der gemeente DEURNE, met dank voor de door hem bewezen diensten. Met ingang van 1 SEPTEMBER aanstaande is op zijn verzoek eervol ontslag verleend aan Dr. DE BRUYN als directeur van het Rijkslandbouwproefstation voor Veevoederonderzoek in WAGENINGEN, onder dankbetuiging voor de door hem bewezen diensten. Het stoffelijk overschot van den beeldhouwer Dr. MENDES DA COSTA is vandaag op de begraafplaats van de Portugeesch Israelitische gemeente in OUDERKERK AAN DEN AMSTEL ten grave gedragen. Onder de talrijke belangstellenden bevonden zich Prof. VAN MOERKERKEN van de Rijksacademie van beeldende kunsten in AMSTERDAM als vertegenwoordiger van den minister van Onderwijs, Kunsten en Wetenschappen, de directeur van de gemeentemusea, Jhr. ROELL namens het geméentebestuur, zijn ambtgenoot uit DEN HAAG, Dr. VAN GELDER, vele kunstbroeders, vrienden, oud-leerlingen en vertegenwoordigers van den kunsthandel. Een 40jarige winkelier uit SMILDE is op zijn motorfiets, bij het passeeren van een melkwagen tegen een hem tegemotkomende auto aangereden en in de DRENT SCHE VAART terecht gekomen. De man was al dood, toen men hem uit het water haald Het 2e inlichtingenbureau van de Nederlandsche spoorwegen is vanmiddag in HAARLEM door den burgemeester, Dr. BARON DE vos VAN STEENWIJK, officieel geopend. WIELRENNEN. De korte, maar moellijke 13e etappe van de RONDE VAN FRANKRIJK van MONTE CAR LO haar SOSPEL en terug over 707 kilometer, gewonnen door den Franschman CALLIEN in 3 UNI 17 min. 56.sec., met munim ongeveer 1½ min. voorsprong op ziin landgenoot PAGeS en den Bel HENDRICKX. Vande Nederlanders werd ALBERT VAN SCHENDEI 110, DE KORVER 206, terwijl DOMINI CUS, TOON VAN SCHENDEL en HELLEMONS grooten achterstand binnenkwamen In het Algemeen Klassement heeft VIETTO de leiding behouden met een totaaltij van 86 uur \" min. 51 sec. voor SILVeRE MAES en VLAEMBUNCK, LAMBRICHTS is 60 gebleven, ALBERT AN SCHENDEL 13e, DOMINICUS verloo 3 plaatsen en staat nu 28e, DE KORVER von daarentegen 1 blaats en is 31e geworden, evenal TOON VAN SCHENDEL, die staat. HELLEMONS verhuisde de 460 naar de 490 plaats. In het lande klassement heeft BELGIE . de leiding voor respectiovelijk BELGI A. en NOORDOOST FRANKRIJK. De Nederlandsche ploeg staat 60. Het kampeerschip TARAKAN is vanochtend om 6 our in ULVIK aangekomen. Ondanks het regenachtige weer was de stemming aan boord uitstekend. WEERSVERWACHTING van het KNMI in DE BILT, geldig tot morgenavond: koel weer met regen- of onweersbuien, betrokken tot zwaar bewolkt, aanvankelijk zwakke tot matigen uiteenloopende wind, later ruimende wind. De wereldconferentie van Christenjeugd is vanmiddag in het CONCERTGEBOUW in AMSTERDAM in openingszitting bijeengeweest. Hierbij heeft PRINS BERNHARD in het Nederlandsch een boodschap voorgelezen van .M.DE KONINGIN, welke als volgt luidt: \"Het is mij een genoegen, die uit alle deelen der wereld zijt samengestroomd, thans in mijn land vereenigd te Mijn goede wenschen vergezellen bij Uwe werkzaamheden. Moge het der jeugd van de geheele wereld gegeven zijn door gemeenschappelijk overleg en gezamenlijken arbeid te streven naar de oplossing van de problemen, die in deze moeilijke tijden niet alleen de jeugd, maar de geheele menschheid bezighouden. Dat in de dagen, die voor liggen, de geest, door welken CHRISTUS in elken mensch doordringt en die alle tegenstellingen en problemen tot oplossing helpt komen, allen tot richtsnoer zij\". Vervolgens richtte PRINS BERNHARD zich in het Engelsch tot de ongeveer 1600 deelnemers aan het Congres: \"Mede namens PRINSES JULIANA verwelkom ik alle afgevaardigden uit ongeveer 70 landen op de eerste wereldconferentie van'Christenjeugd. Temidden van de donkere wolken, de ons in deze dagen omringen, is het voor jonge menschen moeilijk"
    )

    chunks = chunk_text(example_text, max_chars=1000)
    for offset, chunk in chunks:
        print(f"Offset: {offset}, Chunk: {chunk}")