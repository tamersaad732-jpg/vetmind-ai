# -*- coding: utf-8 -*-
"""
VetMind AI - Live Autocomplete & Name Suggestion Engine
Provides instantaneous fuzzy & substring search suggestions for:
- Drug Trade Names (الأسماء التجارية)
- Active Ingredients (المواد الفعالة)
- Clinical Indications & Categories (التصنيفات العلاجية)
"""
import os
from dosage_engine import get_drug_concise_function
from db_engine import get_db

def get_autocomplete_suggestions(query: str, category: str = "", country: str = "", limit: int = 10) -> list:
    """
    Returns live matching suggestions based on the user's keystrokes.
    Prioritizes prefix matches over substring matches.
    """
    clean_q = (query or "").strip()
    if not clean_q or len(clean_q) < 1:
        return []

    conn = get_db()
    c = conn.cursor()

    q_pattern = f"%{clean_q}%"
    q_prefix = f"{clean_q}%"

    sql = """
    SELECT id, country, trade_name, active_ingredient, category, indication, dosage_guide, withdrawal_period
    FROM local_products
    WHERE (trade_name LIKE ? OR active_ingredient LIKE ? OR indication LIKE ?)
    """
    params = [q_pattern, q_pattern, q_pattern]

    if category and category.strip():
        sql += " AND category LIKE ?"
        params.append(f"%{category.strip()}%")

    if country and country.strip() and country.strip() != "all":
        sql += " AND country LIKE ?"
        params.append(f"%{country.strip()}%")

    sql += """
    ORDER BY
      CASE
        WHEN trade_name LIKE ? THEN 1
        WHEN active_ingredient LIKE ? THEN 2
        WHEN trade_name LIKE ? THEN 3
        ELSE 4
      END,
      id ASC
    LIMIT ?
    """
    params.extend([q_prefix, q_prefix, q_pattern, limit])

    c.execute(sql, params)
    rows = c.fetchall()
    conn.close()

    results = []
    seen = set()

    for r in rows:
        t_name = r["trade_name"]
        a_ing = r["active_ingredient"]
        key = (t_name.lower(), a_ing.lower())
        if key in seen:
            continue
        seen.add(key)

        concise_func = get_drug_concise_function(dict(r))
        display_label = f"{t_name} ({concise_func})"

        results.append({
            "id": r["id"],
            "trade_name": t_name,
            "active_ingredient": a_ing,
            "category": r["category"] or "دواء بيطري",
            "indication": r["indication"] or "",
            "function": concise_func,
            "display_label": display_label,
            "dosage_guide": r["dosage_guide"] or "",
            "country": r["country"] or "مصر"
        })

    return results
