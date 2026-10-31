# -*- coding: utf-8 -*-
"""
VetMind AI Enterprise - Giant Arab Clinical Veterinary Compendiums (Data Engine)
Comprehensive data definitions for all 10 Arab veterinary reference textbooks.
Each book is structured with 10 to 12 exhaustive clinical chapters, extensive pathology,
differential matrices, exact pharmacological dosing, surgical techniques, and field case reports.
"""

def get_giant_book_data(ref_id):
    """Returns the comprehensive multi-chapter dataset for any of the 10 Arab books."""
    from giant_data_part1 import GIANT_BOOKS_1_TO_5
    from giant_data_part2 import GIANT_BOOKS_6_TO_10

    if ref_id in GIANT_BOOKS_1_TO_5:
        return GIANT_BOOKS_1_TO_5[ref_id]
    elif ref_id in GIANT_BOOKS_6_TO_10:
        return GIANT_BOOKS_6_TO_10[ref_id]
    return None
