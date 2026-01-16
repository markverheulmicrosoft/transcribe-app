"""
Phrase list for improving Azure Speech recognition of domain-specific terms.

Add words and phrases that are commonly used
to improve transcription accuracy. These can include:
- Names of institutions
- Technical terms
- Proper names that appear frequently

The phrases are used to boost recognition probability during transcription.
"""

# You can add case-specific phrases here
CASE_SPECIFIC_PHRASES: list[str] = [
    # Add names, locations, or terms specific to current cases
]


def get_phrase_list() -> list[str]:
    """Get the complete phrase list for transcription."""
    return CASE_SPECIFIC_PHRASES
