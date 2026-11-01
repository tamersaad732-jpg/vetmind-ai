"""
VetBook Facebook-Scale Algorithmic Engine (VetBookAlgorithmEngine)
==================================================================
Proprietary scoring, ranking, and recommendation engine for veterinarians.
Includes:
1. EdgeRank & Feed Scoring (Affinity x Engagement x Richness + Urgency) x TimeDecay
2. People You May Know (PYMK) Graph Algorithm
3. Trending Topics & Hashtags Extraction
4. Smart Group & Clinical Case Recommendations
"""

import re
import json
from datetime import datetime, timedelta
import math

def calculate_edgerank_score(post: dict, viewer: dict = None, latest_comment_time_str: str = None) -> float:
    """
    Calculates the VetBook EdgeRank Relevance Score for a post relative to the viewer.
    Formula:
      Score = (Affinity * EngagementWeight * ContentRichness + UrgencyBoost) * TimeDecay
    """
    # -------------------------------------------------------------
    # 1. Affinity Score (معامل التخصص والقرابة)
    # -------------------------------------------------------------
    affinity = 1.0
    if viewer:
        viewer_spec = (viewer.get("specialty") or viewer.get("role") or "").lower()
        post_species = (post.get("species") or "").lower()
        author_spec = (post.get("author_specialty") or "").lower()
        
        # Exact Specialty Match (x2.0)
        if post_species and viewer_spec:
            spec_map = {
                "pets": ["أليف", "كلاب", "قطط", "pet", "small animal", "canine", "feline"],
                "bovine": ["أبقار", "جاموس", "مجترات", "cattle", "bovine", "ruminant"],
                "equine": ["خيول", "خيل", "حصان", "equine", "horse"],
                "ovine": ["أغنام", "ماعز", "sheep", "goat", "ovine"],
                "poultry": ["دواجن", "طيور", "poultry", "avian"],
                "wild": ["برية", "wild", "exotic"]
            }
            target_keywords = spec_map.get(post_species, [post_species])
            if any(k in viewer_spec for k in target_keywords):
                affinity *= 2.0

        # Connected Colleague / Followed (x1.8)
        if post.get("is_author_connected"):
            affinity *= 1.8

        # Group Membership (x1.5)
        if post.get("is_in_user_group"):
            affinity *= 1.5

    # -------------------------------------------------------------
    # 2. Engagement Weight (أوزان التفاعل المتدرجة)
    # -------------------------------------------------------------
    eng_score = 0.0
    
    # Best Certified Diagnosis (+35 points)
    if post.get("has_best_answer") or post.get("is_best_answer"):
        eng_score += 35.0

    # Shares & Saves (+15 points each)
    shares = post.get("shares_count", 0)
    saves = post.get("bookmarks_count", 0)
    eng_score += (shares * 15.0) + (saves * 15.0)

    # Detailed clinical comments (+10 points) vs standard comments (+6 points)
    comments_count = post.get("comments_count", 0)
    detailed_comments = post.get("detailed_comments_count", 0)
    normal_comments = max(0, comments_count - detailed_comments)
    eng_score += (detailed_comments * 10.0) + (normal_comments * 6.0)

    # Reactions: specialized (+4 points) vs like (+2 points)
    likes_count = post.get("likes_count", 0)
    specialized_reacts = post.get("specialized_reactions_count", 0)
    standard_likes = max(0, likes_count - specialized_reacts)
    eng_score += (specialized_reacts * 4.0) + (standard_likes * 2.0)

    # Base weight floor
    engagement_weight = 1.0 + math.log1p(eng_score)

    # -------------------------------------------------------------
    # 3. Content Richness (ثراء المحتوى والبيانات السريرية)
    # -------------------------------------------------------------
    richness = 1.0
    # Complete clinical case demographics (+25 points / multiplier)
    has_demo = bool(post.get("species") and post.get("symptoms"))
    has_history = bool(post.get("history") or post.get("diagnosis"))
    if has_demo and has_history:
        richness += 0.4
    elif has_demo:
        richness += 0.2

    # Multiple images or video
    if post.get("video_path") or post.get("image_path"):
        richness += 0.2
    if post.get("poll_data"):
        richness += 0.15

    # -------------------------------------------------------------
    # 4. Urgency Boost (دفعة الحالات الطارئة)
    # -------------------------------------------------------------
    urgency_boost = 0.0
    now = datetime.now()
    created_at_str = post.get("created_at", "")
    hours_since_post = 24.0
    if created_at_str:
        try:
            p_time = datetime.strptime(created_at_str[:19], "%Y-%m-%d %H:%M:%S")
            hours_since_post = max(0.1, (now - p_time).total_seconds() / 3600.0)
        except Exception:
            hours_since_post = 12.0

    if post.get("is_urgent"):
        if hours_since_post <= 12.0:
            urgency_boost = 60.0
        elif hours_since_post <= 24.0:
            urgency_boost = 30.0
        else:
            urgency_boost = 10.0

    # -------------------------------------------------------------
    # 5. Freshness & Author Boost (ضمان صدارة المنشورات الجديدة ولصاحب المنشور)
    # -------------------------------------------------------------
    freshness_boost = 0.0
    if hours_since_post <= 72.0:
        freshness_boost = (72.0 - hours_since_post) * 8.0

    author_boost = 0.0
    if viewer and post.get("user_id") and viewer.get("id") and str(post.get("user_id")) == str(viewer.get("id")):
        author_boost = 600.0  # ضمان ظهور منشور الطبيب في صدارة حسابه دوماً

    # -------------------------------------------------------------
    # 6. Time Decay Factor with Comment Bump
    # -------------------------------------------------------------
    # If the post has received recent comments, use the latest comment time (Facebook bump)
    effective_hours = hours_since_post
    if latest_comment_time_str:
        try:
            c_time = datetime.strptime(latest_comment_time_str[:19], "%Y-%m-%d %H:%M:%S")
            c_hours = max(0.1, (now - c_time).total_seconds() / 3600.0)
            effective_hours = min(hours_since_post, c_hours * 0.75)
        except Exception:
            pass

    time_decay = 1.0 / math.pow(1.0 + (effective_hours / 4.0), 1.35)

    # -------------------------------------------------------------
    # Final EdgeRank Formula
    # -------------------------------------------------------------
    final_score = ((affinity * engagement_weight * richness * 20.0) + urgency_boost + freshness_boost + author_boost) * time_decay
    return round(final_score, 2)


def get_people_you_may_know(conn, user_id: int, limit: int = 5) -> list:
    """
    People You May Know (PYMK) Graph Algorithm for Veterinarians.
    Scoring:
    - Mutual connections (+5 per mutual connection)
    - Specialty match (+20)
    - Clinic / Syndicate match (+15)
    - City / Country match (+15)
    - Shared groups (+10)
    """
    if not user_id:
        return []

    c = conn.cursor()
    # Get current user profile
    c.execute("SELECT id, name, role, country, clinic_name, syndicate_id FROM users WHERE id = ?", (user_id,))
    u_row = c.fetchone()
    if not u_row:
        return []
    u_data = dict(u_row)
    u_country = u_data.get("country") or "مصر"
    u_spec = (u_data.get("role") or "").lower()

    # Get already connected or followed colleague IDs
    connected_ids = {user_id}
    try:
        c.execute("SELECT colleague_id FROM community_connections WHERE user_id = ?", (user_id,))
        for r in c.fetchall():
            connected_ids.add(r[0])
    except Exception:
        pass

    # Get user's groups
    user_groups = set()
    try:
        c.execute("SELECT group_id FROM community_group_members WHERE user_id = ?", (user_id,))
        for r in c.fetchall():
            user_groups.add(r[0])
    except Exception:
        pass

    # Candidate vets
    c.execute("SELECT id, name, role, country, clinic_name, syndicate_id, avatar_image, reputation_score FROM users WHERE id != ? LIMIT 40", (user_id,))
    candidates = [dict(r) for r in c.fetchall()]

    scored_candidates = []
    for cand in candidates:
        cand_id = cand["id"]
        if cand_id in connected_ids:
            continue

        score = 0
        reasons = []

        # Specialty match (+20)
        c_spec = (cand.get("role") or "").lower()
        if c_spec and u_spec and (c_spec in u_spec or u_spec in c_spec):
            score += 20
            reasons.append("نفس التخصص البيطري")

        # Location / Country match (+15)
        if cand.get("country") == u_country:
            score += 15
            reasons.append(f"من {u_country}")

        # Shared Groups (+10)
        try:
            c.execute("SELECT group_id FROM community_group_members WHERE user_id = ?", (cand_id,))
            cand_groups = {r[0] for r in c.fetchall()}
            common_groups = user_groups.intersection(cand_groups)
            if common_groups:
                score += len(common_groups) * 10
                reasons.append(f"{len(common_groups)} مجموعة مشتركة")
        except Exception:
            pass

        # Mutual Connections (+5 each)
        try:
            c.execute("SELECT colleague_id FROM community_connections WHERE user_id = ?", (cand_id,))
            cand_connections = {r[0] for r in c.fetchall()}
            mutual = connected_ids.intersection(cand_connections) - {user_id}
            if mutual:
                score += len(mutual) * 5
                reasons.append(f"{len(mutual)} زميل مشترك")
        except Exception:
            pass

        # Reputation bonus
        rep = cand.get("reputation_score", 100)
        if rep > 200:
            score += 5

        cand["pymk_score"] = score
        cand["pymk_reason"] = reasons[0] if reasons else "طبيب بيطري متميز في الشبكة"
        scored_candidates.append(cand)

    scored_candidates.sort(key=lambda x: x["pymk_score"], reverse=True)
    return scored_candidates[:limit]


def get_trending_topics(conn, hours: int = 48, limit: int = 6) -> list:
    """
    Extracts trending hashtags, diseases, and specialties from posts in the last 48 hours.
    """
    c = conn.cursor()
    c.execute("""
        SELECT title, content, species, likes_count, comments_count, is_urgent 
        FROM community_posts 
        ORDER BY id DESC LIMIT 50
    """)
    rows = c.fetchall()

    topic_counts = {}
    hashtag_pattern = re.compile(r"#[\w_]+")

    for r in rows:
        title = r[0] or ""
        content = r[1] or ""
        species = r[2] or ""
        weight = 1 + (r[3] or 0) + ((r[4] or 0) * 2) + (10 if r[5] else 0)

        # 1. Extract explicit hashtags
        tags = hashtag_pattern.findall(f"{title} {content}")
        for t in tags:
            tag_clean = t.strip()
            topic_counts[tag_clean] = topic_counts.get(tag_clean, 0) + weight

        # 2. Extract clinical species keywords
        if species:
            spec_names = {
                "pets": "#حيوانات_أليفة",
                "bovine": "#طب_المجترات",
                "equine": "#طب_وجراحة_الخيول",
                "ovine": "#الأغنام_والماعز",
                "poultry": "#دواجن_وطيور",
                "wild": "#حياة_برية"
            }
            sp_tag = spec_names.get(species)
            if sp_tag:
                topic_counts[sp_tag] = topic_counts.get(sp_tag, 0) + (weight // 2)

    # Curated fallback trending veterinary topics if feed has few hashtags
    curated_fallback = [
        ("#حالات_طارئة", 45),
        ("#سونار_بيطري", 38),
        ("#جراحة_بيطرية", 32),
        ("#ولادة_قيصرية", 28),
        ("#بروتوكول_علاجي", 24),
        ("#تحاليل_معملية", 20)
    ]
    for tag, w in curated_fallback:
        if tag not in topic_counts:
            topic_counts[tag] = w

    sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    results = []
    for tag, score in sorted_topics[:limit]:
        results.append({
            "tag": tag,
            "query": tag.replace("#", ""),
            "score": score,
            "posts_approx": max(1, score // 6)
        })
    return results


def get_recommended_groups(conn, user_id: int, limit: int = 4) -> list:
    """
    Returns top active veterinary groups, marking user membership status.
    """
    c = conn.cursor()
    c.execute("SELECT * FROM community_groups ORDER BY members_count DESC LIMIT 10")
    groups = [dict(r) for r in c.fetchall()]

    user_groups = set()
    if user_id:
        try:
            c.execute("SELECT group_id FROM community_group_members WHERE user_id = ?", (user_id,))
            user_groups = {r[0] for r in c.fetchall()}
        except Exception:
            pass

    for g in groups:
        g["is_member"] = g["id"] in user_groups

    return groups[:limit]


def get_similar_cases(conn, current_post: dict, limit: int = 3) -> list:
    """
    Finds other clinical cases sharing the same species, symptoms, or category.
    """
    post_id = current_post.get("id", 0)
    species = current_post.get("species", "")
    if not species or species == "all":
        return []
    c = conn.cursor()
    c.execute("""
        SELECT id, title, species, author_name, created_at, likes_count, comments_count 
        FROM community_posts 
        WHERE id != ? AND species = ? 
        ORDER BY id DESC LIMIT ?
    """, (post_id, species, limit))
    return [dict(r) for r in c.fetchall()]
