"""
Phrase list for improving Azure Speech recognition of domain-specific terms.

Add words and phrases that are commonly used in Raad van State proceedings
to improve transcription accuracy. These can include:
- Legal terminology
- Names of institutions
- Technical terms
- Proper names that appear frequently

The phrases are used to boost recognition probability during transcription.
"""

# Dutch legal/administrative law terms for Raad van State
RAAD_VAN_STATE_PHRASES = [
    # Institution names
    "Raad van State",
    "Afdeling bestuursrechtspraak",
    "Afdeling advisering",
    "Rechtbank",
    "Hoge Raad",
    "Centrale Raad van Beroep",
    "College van Beroep voor het bedrijfsleven",
    "CBb",
    "CRvB",
    "Eerste Kamer",
    "Tweede Kamer",
    "Staten-Generaal",
    
    # Legal roles & titles
    "appellant",
    "appellante",
    "appellanten",
    "verweerder",
    "verweerster",
    "gemachtigde",
    "staatsraad",
    "staatsraden",
    "griffier",
    "advocaat",
    "mr.",
    "meester",
    "rechter",
    "rechters",
    "advocaat-generaal",
    "procureur-generaal",
    "landsadvocaat",
    "derde-partij",
    "derde-belanghebbende",
    "belanghebbende",
    "belanghebbenden",
    "partijen",
    "eiser",
    "eiseres",
    "gedaagde",
    
    # Procedural terms
    "hoger beroep",
    "beroepschrift",
    "verweerschrift",
    "pleitnota",
    "pleidooi",
    "repliek",
    "dupliek",
    "memorie",
    "incidenteel appel",
    "incidenteel hoger beroep",
    "voorlopige voorziening",
    "schorsingsverzoek",
    "ontvankelijkheid",
    "niet-ontvankelijk",
    "ontvankelijk",
    "gegrond",
    "ongegrond",
    "kennelijk ongegrond",
    "kennelijk niet-ontvankelijk",
    
    # Legal documents & decisions
    "rechtsbijstand",
    "proceskosten",
    "griffierecht",
    "uitspraak",
    "vonnis",
    "arrest",
    "beschikking",
    "besluit",
    "beslissing",
    "tussenuitspraak",
    "einduitspraak",
    "bestuurlijke lus",
    
    # Administrative law - Awb
    "Algemene wet bestuursrecht",
    "Awb",
    "bestuursorgaan",
    "bestuursorganen",
    "bezwaarschrift",
    "bezwaarprocedure",
    "beroepsprocedure",
    "zorgvuldigheidsbeginsel",
    "motiveringsbeginsel",
    "evenredigheidsbeginsel",
    "rechtszekerheidsbeginsel",
    "vertrouwensbeginsel",
    "gelijkheidsbeginsel",
    "fair play beginsel",
    "verbod van détournement de pouvoir",
    "willekeur",
    "marginale toetsing",
    
    # Specific law areas often at RvS
    "omgevingsrecht",
    "ruimtelijke ordening",
    "bestemmingsplan",
    "omgevingsvergunning",
    "milieuvergunning",
    "Wet ruimtelijke ordening",
    "Wro",
    "Omgevingswet",
    "Wet algemene bepalingen omgevingsrecht",
    "Wabo",
    "vreemdelingenrecht",
    "Vreemdelingenwet",
    "verblijfsvergunning",
    "asiel",
    "IND",
    "Immigratie- en Naturalisatiedienst",
    
    # Hearing/procedure terms
    "zitting",
    "mondelinge behandeling",
    "ter zitting",
    "behandeling ter zitting",
    "getuige",
    "getuigen",
    "deskundige",
    "deskundigen",
    "comparitie",
    "onderzoek ter plaatse",
    "descente",
    
    # Common phrases in hearings
    "voorzitter",
    "edelachtbare",
    "edelgrootachtbare",
    "geachte",
    "concluderend",
    "samengevat",
    "in casu",
    "ondergetekende",
    "primair",
    "subsidiair",
    "meer subsidiair",
    "in beginsel",
    "naar mijn mening",
    "ik verwijs naar",
    "zoals blijkt uit",
    "ten aanzien van",
    "met betrekking tot",
    "gelet op",
    "ingevolge",
    "krachtens",
    "op grond van",
    "in strijd met",
    "conform",
    "aldus",
    "derhalve",
    "mitsdien",
    "dientengevolge",
    
    # Evidence & argumentation
    "bewijslast",
    "bewijsmiddel",
    "bewijsmiddelen",
    "bewijs",
    "stukken",
    "gedingstukken",
    "producties",
    "bijlagen",
    "dossierstuk",
    "processtuk",
    
    # Remedies & outcomes
    "vernietiging",
    "vernietigen",
    "terugverwijzing",
    "terugverwijzen",
    "schadevergoeding",
    "dwangsom",
    "bestuursdwang",
    "last onder dwangsom",
    "last onder bestuursdwang",
    "intrekking",
    "herroeping",
    "wijziging",
    
    # Time-related legal terms
    "termijn",
    "beroepstermijn",
    "bezwaartermijn",
    "fatale termijn",
    "pro forma",
    "tijdig",
    "niet tijdig",
    "tardief",
    
    # Other common terms
    "artikel",
    "lid",
    "sub",
    "juncto",
    "jo",
    "et cetera",
    "rechtspraak",
    "jurisprudentie",
    "vaste rechtspraak",
    "bestendige jurisprudentie",
]

# You can add case-specific phrases here
CASE_SPECIFIC_PHRASES: list[str] = [
    # Add names, locations, or terms specific to current cases
]


def get_phrase_list() -> list[str]:
    """Get the complete phrase list for transcription."""
    return RAAD_VAN_STATE_PHRASES + CASE_SPECIFIC_PHRASES
