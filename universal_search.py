# -*- coding: utf-8 -*-
"""
VetMind AI - Universal Platform Search Engine
Searches comprehensively across:
1. Veterinary Medicines & Pharmacy (local_products)
2. Scientific References & Books (ARAB_FULL_BOOKS, GLOBAL_FULL_BOOKS)
3. 30 Clinical Tools & Calculators (interactive_tools)
4. Veterinary Contraindications & Toxicities (contraindications_data)
5. Clinic Records & Cases (cases, appointments, animals)
6. VetBook Community Posts & Cases (community_posts)
"""
import os
import sqlite3
from references_content_data import ARAB_FULL_BOOKS, GLOBAL_FULL_BOOKS

DB_PATH = os.path.join(os.path.dirname(__file__), "vetmind.db")

# Catalog of the 30 Clinical Tools & Hubs for Instant Search Matching
CLINICAL_TOOLS_CATALOG = [
    {
        "id": "fluid-therapy",
        "title": "حاسبة المحاليل الوريدية والتعويضية (Fluid Therapy Calculator)",
        "keywords": ["محاليل", "جفاف", "وريد", "رينجر", "دكستروز", "fluid", "hydration", "dehydration", "iv"],
        "category": "الأدوات السريرية",
        "url": "/tools/fluid-therapy",
        "icon": "💧",
        "summary": "حساب السوائل الوريدية ومعدل التنقيط لتعويض الجفاف والحفاظ على استقرار الحيوان."
    },
    {
        "id": "anesthesia-protocol",
        "title": "مخطط بروتوكول التخدير والمهدئات (Anesthesia Protocol Planner)",
        "keywords": ["تخدير", "مهدئ", "زايلازين", "كيتامين", "بروبوفول", "anesthesia", "sedation", "xylazine", "ketamine"],
        "category": "الأدوات السريرية",
        "url": "/tools/anesthesia-protocol",
        "icon": "💉",
        "summary": "تخطيط بروتوكولات التخدير العام والموضعي وحساب جرعات المهدئات بدقة."
    },
    {
        "id": "toxicology-calc",
        "title": "حاسبة التسمم والإسعافات الطارئة (Toxicology Emergency Calculator)",
        "keywords": ["تسمم", "سم", "ترياق", "سموم", "شيكولاتة", "فحم", "toxicology", "poison", "antidote"],
        "category": "الأدوات السريرية",
        "url": "/tools/toxicology-calc",
        "icon": "⚠️",
        "summary": "تقييم درجات التسمم وحساب جرعات مضادات السموم والترياق الإسعافي."
    },
    {
        "id": "contraindications",
        "title": "دليل الممنوعات البيطرية في الحيوان (Contraindications & Toxins)",
        "keywords": ["ممنوعات", "سميات", "ممنوع", "باراسيتامول", "أطعمة سامة", "قطط", "كلاب", "contraindications", "toxic"],
        "category": "دليل الممنوعات",
        "url": "/contraindications",
        "icon": "⛔",
        "summary": "الدليل الشامل لكافة الأدوية والأطعمة والنباتات الممنوعة والسامة لكل نوع حيوان."
    },
    {
        "id": "interactions",
        "title": "فاحص التداخلات الدوائية والسلامة (Drug-Drug Interactions Checker)",
        "keywords": ["تداخلات", "تضاد", "تآزر", "أدوية", "interaction", "synergy", "antagonism", "drugs"],
        "category": "الأدوات الدوائية",
        "url": "/interactions",
        "icon": "🔄",
        "summary": "فحص توافق وتضاد أي دوائين بيطريين من قاعدة بيانات الـ 1,005 دواء فورياً."
    },
    {
        "id": "gestation-calc",
        "title": "حاسبة الحمل وموعد الولادة المتوقع (Gestation & Parturition Calculator)",
        "keywords": ["حمل", "عشار", "ولادة", "توليد", "موعد الولادة", "gestation", "pregnancy", "parturition"],
        "category": "الأدوات السريرية",
        "url": "/tools/gestation-calc",
        "icon": "📅",
        "summary": "حساب مواعيد الولادة المتوقعة وجداول المتابعة لكافة أنواع الحيوانات."
    },
    {
        "id": "blood-transfusion",
        "title": "حاسبة نقل الدم ومطابقة الفصائل (Blood Transfusion Calculator)",
        "keywords": ["نقل دم", "دم", "هيماتوكريت", "أنيميا", "فقر دم", "blood", "transfusion", "anemia"],
        "category": "الأدوات السريرية",
        "url": "/tools/blood-transfusion",
        "icon": "🩸",
        "summary": "حساب حجم الدم المطلوب نقله في حالات فقر الدم الحاد والنزيف."
    },
    {
        "id": "pain-scale",
        "title": "مقياس تقييم الألم البيطري (Veterinary Pain Scoring Scale)",
        "keywords": ["ألم", "مسكن", "تقييم الألم", "غلاسكو", "pain", "scale", "glasgow"],
        "category": "الأدوات السريرية",
        "url": "/tools/pain-scale",
        "icon": "🩺",
        "summary": "تقييم موضوعي لدرجات الألم في الحيوانات وتحديد التدخل المسكن المناسب."
    },
    {
        "id": "nutrition-calc",
        "title": "حاسبة الاحتياجات الغذائية والطاقة (MER / RER Nutrition Calculator)",
        "keywords": ["تغذية", "سعرات", "طاقة", "عليقة", "nutrition", "calories", "rer", "mer"],
        "category": "الأدوات السريرية",
        "url": "/tools/nutrition-calc",
        "icon": "🥗",
        "summary": "حساب الاحتياجات اليومية من الطاقة والسعرات الحرارية للحيوانات المريضة والسليمة."
    },
    {
        "id": "bcs-evaluator",
        "title": "مقياس درجات الحالة الجسدية (Body Condition Score - BCS)",
        "keywords": ["حالة جسدية", "سمنة", "نحافة", "bcs", "body condition"],
        "category": "الأدوات السريرية",
        "url": "/tools/bcs-evaluator",
        "icon": "⚖️",
        "summary": "تقييم دهون الجسم وحالة التغذية للمجترات والخيول والحيوانات الأليفة."
    },
    {
        "id": "cmt-mastitis",
        "title": "دليل تقييم التهاب الضرع الميداني (CMT Mastitis Evaluator)",
        "keywords": ["ضرع", "كاليفورنيا", "حليب", "التهاب الضرع", "mastitis", "cmt", "udder"],
        "category": "الأدوات السريرية",
        "url": "/tools/cmt-mastitis",
        "icon": "🥛",
        "summary": "تفسير اختبار كاليفورنيا للضرع وخطة علاج التهاب الضرع السريري وتحت السريري."
    },
    {
        "id": "renal-calc",
        "title": "حاسبة وظائف الكلى ومعدل الفلترة (IRIS Renal Failure Staging)",
        "keywords": ["كلى", "كرياتينين", "فشل كلوي", "بول", "renal", "kidney", "iris", "creatinine"],
        "category": "الأدوات السريرية",
        "url": "/tools/renal-calc",
        "icon": "🫘",
        "summary": "تصنيف مراحل القصور الكلوي وفق معايير الجمعية الدولية لأمراض الكلى (IRIS)."
    },
    {
        "id": "electrolyte-correction",
        "title": "حاسبة تصحيح الشوارد والبيكربونات (Electrolyte Correction Calculator)",
        "keywords": ["شوارد", "بوتاسيوم", "صوديوم", "حموضة", "بيكربونات", "electrolytes", "bicarbonate", "potassium"],
        "category": "الأدوات السريرية",
        "url": "/tools/electrolyte-correction",
        "icon": "⚡",
        "summary": "حساب جرعات تصحيح نقص البوتاسيوم والصوديوم وعلاج حموضة الدم."
    },
    {
        "id": "poultry-water-calc",
        "title": "حاسبة استهلاك مياه وأدوية الدواجن (Poultry Water Medication Calculator)",
        "keywords": ["دواجن", "فراخ", "طيور", "عنبر", "مياه", "poultry", "water", "broiler"],
        "category": "الأدوات السريرية",
        "url": "/tools/poultry-water-calc",
        "icon": "🐔",
        "summary": "حساب كميات مياه الشرب وتوزيع الأدوية واللقاحات لقطعان الدواجن بدقة."
    },
    {
        "id": "auscultation-guide",
        "title": "مسرد الأصوات القلبية والتنفسية البيطرية (Auscultation Guide)",
        "keywords": ["سماعة", "أصوات", "قلب", "رئة", "حشرجة", "خرخرة", "auscultation", "heart", "lungs"],
        "category": "الأدوات السريرية",
        "url": "/tools/auscultation-guide",
        "icon": "🎧",
        "summary": "دليل إكلينيكي صوتي ووصف مفصل لأصوات القلب والرئة الطبيعية والمرضية."
    },
    {
        "id": "tools-hub",
        "title": "دليل الأدوات الإكلينيكية الـ 30 الشامل (All 30 Clinical Tools)",
        "keywords": ["أدوات", "حاسبات", "دليل الأدوات", "tools", "calculators"],
        "category": "فهرس الأدوات",
        "url": "/tools",
        "icon": "🛠️",
        "summary": "الفهرس الكامل للباقة المتكاملة لـ 30 أداة وحاسبة إكلينيكية بيطرية."
    },
    {
        "id": "references-library",
        "title": "مكتبة المراجع والكتب البيطرية الـ 30 (Veterinary Reference Library)",
        "keywords": ["مراجع", "كتب", "مكتبة", "مرجع", "كتب بيطرية", "references", "library", "books"],
        "category": "المكتبة العلمية",
        "url": "/references",
        "icon": "📚",
        "summary": "30 مرجعاً علمياً ودولياً كاملاً للقراءة والتحميل المباشر."
    },
    {
        "id": "pharmacy",
        "title": "الصيدلية البيطرية الذكية (1,005 دواء ومستحضر)",
        "keywords": ["صيدلية", "أدوية", "دواء", "مضاد حيوي", "فارما", "pharmacy", "drugs"],
        "category": "الصيدلية",
        "url": "/pharmacy",
        "icon": "💊",
        "summary": "دليل الأدوية البيطرية الشامل مع الجرعات وفترات السحب والأسعار."
    },
    {
        "id": "clinic",
        "title": "سجلات وحالات العيادة البيطرية (Clinic Management & Cases)",
        "keywords": ["عيادة", "حالات", "كشف", "روشتة", "سجلات", "clinic", "cases", "prescription"],
        "category": "العيادة",
        "url": "/clinic",
        "icon": "🏥",
        "summary": "إدارة كشوفات وحالات الحيوانات وطباعة الروشتات ومتابعة التطعيمات."
    },
    {
        "id": "community",
        "title": "مجتمع الأطباء البيطريين VetBook (Veterinary Social Network)",
        "keywords": ["مجتمع", "فيسبوك", "بوستات", "حالات سريرية", "زملاء", "vetbook", "community"],
        "category": "مجتمع الأطباء",
        "url": "/community",
        "icon": "🌐",
        "summary": "الشبكة الاجتماعية والمهنية التفاعلية الأولى للأطباء البيطريين."
    }
]

def search_all_platform(query: str, category_filter: str = "all", limit: int = 30) -> dict:
    """
    Master search across all platform entities:
    - Drugs
    - References
    - Tools
    - Contraindications
    - Clinic records
    - Community posts
    """
    clean_q = (query or "").strip().lower()
    if not clean_q:
        return {"total": 0, "results": [], "counts": {}}

    results = {
        "drugs": [],
        "references": [],
        "tools": [],
        "contraindications": [],
        "community": [],
        "clinic": []
    }

    # 1. Search Clinical Tools & Hubs
    for tool in CLINICAL_TOOLS_CATALOG:
        match_title = clean_q in tool["title"].lower()
        match_summary = clean_q in tool["summary"].lower()
        match_keyword = any(clean_q in k.lower() or k.lower() in clean_q for k in tool["keywords"])
        if match_title or match_summary or match_keyword:
            results["tools"].append({
                "type": "tool",
                "badge": "أداة سريرية 🛠️",
                "title": tool["title"],
                "subtitle": tool["category"],
                "description": tool["summary"],
                "url": tool["url"],
                "icon": tool["icon"],
                "score": 10 if match_title else 5
            })

    # 2. Search 30 Scientific References & Books
    # Arab references
    for ref_id, ref in ARAB_FULL_BOOKS.items():
        title = ref.get("title", "")
        summary = ref.get("summary", "")
        species = ref.get("species", "")
        citation = ref.get("citation", "")
        match_title = clean_q in title.lower()
        match_summary = clean_q in summary.lower()
        match_species = clean_q in species.lower()
        match_citation = clean_q in citation.lower()

        if match_title or match_summary or match_species or match_citation:
            results["references"].append({
                "type": "reference",
                "badge": "مرجع عربي معتمد 🇪🇬",
                "title": f"كتاب: {title}",
                "subtitle": f"الأنواع: {species[:60]}...",
                "description": summary[:160] + "...",
                "url": f"/references/read/{ref_id}",
                "download_url": f"/references/download/{ref_id}",
                "icon": "📚",
                "score": 10 if match_title else 4
            })

    # Global references
    for ref_id, ref in GLOBAL_FULL_BOOKS.items():
        title = ref.get("title", "")
        summary = ref.get("summary", "")
        species = ref.get("species", "")
        citation = ref.get("citation", "")
        match_title = clean_q in title.lower()
        match_summary = clean_q in summary.lower()
        match_species = clean_q in species.lower()
        match_citation = clean_q in citation.lower()

        if match_title or match_summary or match_species or match_citation:
            results["references"].append({
                "type": "reference",
                "badge": "مرجع دولي Tier-1 🌐",
                "title": f"Book: {title}",
                "subtitle": f"Coverage: {species[:60]}...",
                "description": summary[:160] + "...",
                "url": f"/references/read/{ref_id}",
                "download_url": f"/references/download/{ref_id}",
                "icon": "📚",
                "score": 10 if match_title else 4
            })

    # 3. Search Veterinary Contraindications (from contraindications_data)
    try:
        from contraindications_data import search_contraindications
        c_matches = search_contraindications(clean_q)
        for item in c_matches:
            results["contraindications"].append({
                "type": "contraindication",
                "badge": f"ممنوع في {item['species_name']} ⛔",
                "title": f"ممنوع: {item['substance_name']} في {item['species_name']}",
                "subtitle": f"درجة الخطر: {item['danger_level_title']}",
                "description": item['reason'][:160] + "...",
                "url": f"/contraindications?species={item['species_code']}&q={clean_q}",
                "icon": "⛔",
                "score": 8
            })
    except Exception as e:
        pass

    # 4. Search Database: Drugs, Clinic & Community
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # A) Drugs (local_products)
        q_like = f"%{clean_q}%"
        c.execute("""
            SELECT id, trade_name, active_ingredient, category, indication, country, dosage_guide
            FROM local_products
            WHERE trade_name LIKE ? OR active_ingredient LIKE ? OR indication LIKE ? OR category LIKE ?
            ORDER BY 
              CASE WHEN trade_name LIKE ? THEN 1 WHEN active_ingredient LIKE ? THEN 2 ELSE 3 END
            LIMIT 15
        """, (q_like, q_like, q_like, q_like, f"{clean_q}%", f"{clean_q}%"))
        drug_rows = c.fetchall()

        for dr in drug_rows:
            results["drugs"].append({
                "type": "drug",
                "badge": f"دواء بيطري ({dr['country'] or 'معتمد'}) 💊",
                "title": dr["trade_name"],
                "subtitle": f"المادة الفعالة: {dr['active_ingredient']}",
                "description": f"التصنيف: {dr['category']} • دواعي الاستعمال: {(dr['indication'] or '')[:120]}...",
                "url": f"/pharmacy?q={dr['trade_name']}",
                "icon": "💊",
                "score": 9
            })

        # B) Community Posts (community_posts)
        try:
            c.execute("""
                SELECT id, title, content, author_name, category, likes_count
                FROM community_posts
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY likes_count DESC, id DESC
                LIMIT 8
            """, (q_like, q_like))
            comm_rows = c.fetchall()
            for cp in comm_rows:
                results["community"].append({
                    "type": "community",
                    "badge": "منشور مجتمع VetBook 🌐",
                    "title": cp["title"] or f"حالة سريرية من د. {cp['author_name']}",
                    "subtitle": f"الكاتب: د. {cp['author_name']} • القسم: {cp['category']}",
                    "description": (cp["content"] or "")[:150] + "...",
                    "url": f"/community#post-{cp['id']}",
                    "icon": "🌐",
                    "score": 6
                })
        except:
            pass

        # C) Clinic Cases (cases)
        try:
            c.execute("""
                SELECT id, animal_name, species, diagnosis, symptoms, client_name
                FROM cases
                WHERE animal_name LIKE ? OR species LIKE ? OR diagnosis LIKE ? OR symptoms LIKE ?
                LIMIT 6
            """, (q_like, q_like, q_like, q_like))
            case_rows = c.fetchall()
            for cs in case_rows:
                results["clinic"].append({
                    "type": "clinic",
                    "badge": "سجل عيادة 🏥",
                    "title": f"حالة: {cs['animal_name']} ({cs['species']})",
                    "subtitle": f"التشخيص: {cs['diagnosis'] or 'قيد الفحص'} • المربي: {cs['client_name']}",
                    "description": f"الأعراض: {(cs['symptoms'] or '')[:120]}...",
                    "url": f"/clinic",
                    "icon": "🏥",
                    "score": 7
                })
        except:
            pass

        conn.close()
    except Exception as e:
        print("Database search error:", e)

    # Flatten and sort by relevance score
    all_combined = []
    counts = {}
    for cat_key, items in results.items():
        counts[cat_key] = len(items)
        if category_filter == "all" or category_filter == cat_key:
            all_combined.extend(items)

    all_combined.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "query": clean_q,
        "total": len(all_combined),
        "counts": counts,
        "results": all_combined[:limit]
    }

def get_universal_autocomplete_suggestions(query: str, limit: int = 10) -> list:
    """
    Lightning-fast multi-category autocomplete for instant live typing preview in the topbar & search modal.
    """
    clean_q = (query or "").strip().lower()
    if not clean_q or len(clean_q) < 1:
        return []

    suggestions = []

    # 1. Matching Tools
    for t in CLINICAL_TOOLS_CATALOG:
        if clean_q in t["title"].lower() or any(clean_q in k.lower() for k in t["keywords"]):
            suggestions.append({
                "type": "tool",
                "icon": t["icon"],
                "label": t["title"],
                "category": t["category"],
                "url": t["url"]
            })
            if len(suggestions) >= 3:
                break

    # 2. Matching References
    ref_count = 0
    for ref_id, ref in {**ARAB_FULL_BOOKS, **GLOBAL_FULL_BOOKS}.items():
        if clean_q in ref.get("title", "").lower() or clean_q in ref.get("species", "").lower():
            suggestions.append({
                "type": "reference",
                "icon": "📚",
                "label": ref.get("title", ""),
                "category": "مرجع بيطري معتمد",
                "url": f"/references/read/{ref_id}"
            })
            ref_count += 1
            if ref_count >= 3:
                break

    # 3. Matching Contraindications
    try:
        from contraindications_data import search_contraindications
        c_matches = search_contraindications(clean_q)
        for cm in c_matches[:3]:
            suggestions.append({
                "type": "contraindication",
                "icon": "⛔",
                "label": f"ممنوع: {cm['substance_name']} في {cm['species_name']}",
                "category": "ممنوعات وسميات",
                "url": f"/contraindications?species={cm['species_code']}&q={clean_q}"
            })
    except:
        pass

    # 4. Matching Drugs from DB
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT trade_name, active_ingredient, category
            FROM local_products
            WHERE trade_name LIKE ? OR active_ingredient LIKE ?
            ORDER BY CASE WHEN trade_name LIKE ? THEN 1 ELSE 2 END
            LIMIT 5
        """, (f"%{clean_q}%", f"%{clean_q}%", f"{clean_q}%"))
        rows = c.fetchall()
        for r in rows:
            suggestions.append({
                "type": "drug",
                "icon": "💊",
                "label": f"{r['trade_name']} ({r['active_ingredient']})",
                "category": r["category"] or "دواء بيطري",
                "url": f"/pharmacy?q={r['trade_name']}"
            })
        conn.close()
    except:
        pass

    # Also suggest Universal Search query if user wants to see all
    suggestions.append({
        "type": "all",
        "icon": "🔍",
        "label": f'البحث الشامل عن "{clean_q}" في المنصة بالكامل...',
        "category": "بحث شامل",
        "url": f"/search?q={clean_q}"
    })

    return suggestions[:limit]
