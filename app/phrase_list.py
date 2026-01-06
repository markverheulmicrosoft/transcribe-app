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
    
    # Legal roles
    "appellant",
    "appellante",
    "verweerder",
    "gemachtigde",
    "staatsraad",
    "griffier",
    
    # Legal terms
    "hoger beroep",
    "beroepschrift",
    "verweerschrift",
    "pleitnota",
    "rechtsbijstand",
    "proceskosten",
    "griffierecht",
    "bestuursorgaan",
    "zitting",
    "uitspraak",
    
    # Administrative law
    "Algemene wet bestuursrecht",
    "Awb",
    "beschikking",
    "bezwaarschrift",
    "bezwaarprocedure",
    "beroepsprocedure",
    
    # Common phrases
    "voorzitter",
    "edelachtbare",
    "geachte",
    "concluderend",
    "samengevat",
]

# You can add case-specific phrases here
CASE_SPECIFIC_PHRASES: list[str] = [
    # Add names, locations, or terms specific to current cases
]


def get_phrase_list() -> list[str]:
    """Get the complete phrase list for transcription."""
    return RAAD_VAN_STATE_PHRASES + CASE_SPECIFIC_PHRASES
