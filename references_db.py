# -*- coding: utf-8 -*-
"""
VetMind AI International Scientific & Clinical References Database
10 Authoritative Arab & Regional References + 20 Global Tier-1 References
All citations, summaries, and direct file download mappings verified.
"""

from generate_clean_references import ARAB_REFS as ARAB_REFERENCES, GLOBAL_REFS as GLOBAL_REFERENCES

ALL_REFERENCES = ARAB_REFERENCES + GLOBAL_REFERENCES

def get_all_references():
    return ALL_REFERENCES

def get_arab_references():
    return ARAB_REFERENCES

def get_global_references():
    return GLOBAL_REFERENCES

def get_reference_by_id(ref_id: str):
    for r in ALL_REFERENCES:
        if r["id"] == ref_id:
            return r
    return None
