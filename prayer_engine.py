# -*- coding: utf-8 -*-
"""
VetMind AI - Islamic Prayer Times Engine & Clinical Schedule Notifier
Supports all Arab capital cities and custom locations with next prayer countdown.
"""
from datetime import datetime, date
import math

# City Coordinates & Timezones (Latitude, Longitude, Timezone Offset, Method)
CITIES_DB = {
    "القاهرة (مصر)": {"lat": 30.0444, "lng": 31.2357, "tz": 2, "method": "Egypt"},
    "الإسكندرية (مصر)": {"lat": 31.2001, "lng": 29.9187, "tz": 2, "method": "Egypt"},
    "الجيزة (مصر)": {"lat": 30.0131, "lng": 31.2089, "tz": 2, "method": "Egypt"},
    "المنصورة (مصر)": {"lat": 31.0409, "lng": 31.3785, "tz": 2, "method": "Egypt"},
    "طنطا (مصر)": {"lat": 30.7865, "lng": 31.0004, "tz": 2, "method": "Egypt"},
    "أسيوط (مصر)": {"lat": 27.1809, "lng": 31.1837, "tz": 2, "method": "Egypt"},
    "الرياض (السعودية)": {"lat": 24.7136, "lng": 46.6753, "tz": 3, "method": "Makkah"},
    "مكة المكرمة (السعودية)": {"lat": 21.3891, "lng": 39.8579, "tz": 3, "method": "Makkah"},
    "المدينة المنورة (السعودية)": {"lat": 24.5247, "lng": 39.5692, "tz": 3, "method": "Makkah"},
    "جدة (السعودية)": {"lat": 21.4858, "lng": 39.1925, "tz": 3, "method": "Makkah"},
    "الدمام (السعودية)": {"lat": 26.4207, "lng": 50.0888, "tz": 3, "method": "Makkah"},
    "القصيم / بريدة (السعودية)": {"lat": 26.3260, "lng": 43.9750, "tz": 3, "method": "Makkah"},
    "أبوظبي (الإمارات)": {"lat": 24.4539, "lng": 54.3773, "tz": 4, "method": "Gulf"},
    "دبي (الإمارات)": {"lat": 25.2048, "lng": 55.2708, "tz": 4, "method": "Gulf"},
    "العين (الإمارات)": {"lat": 24.2075, "lng": 55.7447, "tz": 4, "method": "Gulf"},
    "عمان (الأردن)": {"lat": 31.9454, "lng": 35.9284, "tz": 3, "method": "MWL"},
    "بغداد (العراق)": {"lat": 33.3152, "lng": 44.3661, "tz": 3, "method": "MWL"},
    "الخرطوم (السودان)": {"lat": 15.5007, "lng": 32.5599, "tz": 2, "method": "Egypt"},
    "الكويت (الكويت)": {"lat": 29.3759, "lng": 47.9774, "tz": 3, "method": "Gulf"},
    "الدوحة (قطر)": {"lat": 25.2854, "lng": 51.5310, "tz": 3, "method": "Gulf"},
    "المنامة (البحرين)": {"lat": 26.2285, "lng": 50.5860, "tz": 3, "method": "Gulf"},
    "مسقط (عمان)": {"lat": 23.5880, "lng": 58.3829, "tz": 4, "method": "Gulf"},
    "الرباط (المغرب)": {"lat": 34.0209, "lng": -6.8416, "tz": 1, "method": "MWL"},
    "الجزائر (الجزائر)": {"lat": 36.7538, "lng": 3.0588, "tz": 1, "method": "MWL"},
    "تونس (تونس)": {"lat": 36.8065, "lng": 10.1815, "tz": 1, "method": "MWL"},
    "طرابلس (ليبيا)": {"lat": 32.8872, "lng": 13.1913, "tz": 2, "method": "MWL"}
}

PRAYER_LOCALIZED_NAMES = {
    "fajr": {"ar": "صلاة الفجر", "en": "Fajr Prayer", "fr": "Prière du Fajr", "de": "Fadschr-Gebet", "es": "Oración del Fajr", "it": "Preghiera Fajr", "zh": "晨礼 (Fajr)", "ja": "夜明けの礼拝 (Fajr)"},
    "sunrise": {"ar": "الشروق", "en": "Sunrise", "fr": "Lever du soleil", "de": "Sonnenaufgang", "es": "Amanecer", "it": "Alba", "zh": "日出", "ja": "日の出"},
    "dhuhr": {"ar": "صلاة الظهر", "en": "Dhuhr Prayer", "fr": "Prière du Dohr", "de": "Dhuhr-Gebet", "es": "Oración del Dhuhr", "it": "Preghiera Dhuhr", "zh": "晌礼 (Dhuhr)", "ja": "正午の礼拝 (Dhuhr)"},
    "asr": {"ar": "صلاة العصر", "en": "Asr Prayer", "fr": "Prière de l'Asr", "de": "Asr-Gebet", "es": "Oración del Asr", "it": "Preghiera Asr", "zh": "晡礼 (Asr)", "ja": "午後の礼拝 (Asr)"},
    "maghrib": {"ar": "صلاة المغرب", "en": "Maghrib Prayer", "fr": "Prière du Maghreb", "de": "Maghrib-Gebet", "es": "Oración del Magreb", "it": "Preghiera Maghreb", "zh": "昏礼 (Maghrib)", "ja": "日没の礼拝 (Maghrib)"},
    "isha": {"ar": "صلاة العشاء", "en": "Isha Prayer", "fr": "Prière de l'Isha", "de": "Ischa-Gebet", "es": "Oración de Isha", "it": "Preghiera Isha", "zh": "宵礼 (Isha)", "ja": "夜の礼拝 (Isha)"}
}

def calculate_prayer_times(city_name: str = "القاهرة (مصر)", target_date: date = None, lang: str = "ar") -> dict:
    """
    Computes solar-calculated prayer times for the given city, date, and user language.
    Returns: Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha, Next Prayer, Countdown.
    """
    clean_lang = (lang or "ar").strip().lower()
    if clean_lang not in ["ar", "en", "fr", "de", "es", "it", "zh", "ja"]:
        clean_lang = "ar"
    if target_date is None:
        target_date = date.today()

    city_info = CITIES_DB.get(city_name, CITIES_DB["القاهرة (مصر)"])
    lat = city_info["lat"]
    lng = city_info["lng"]
    tz = city_info["tz"]
    method = city_info.get("method", "Egypt")

    # Day of year
    N = target_date.timetuple().tm_yday

    # Approximate equation of time & solar declination
    B = 2.0 * math.pi * (N - 81) / 365.0
    EoT = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B) # minutes
    delta = math.asin(math.sin(math.radians(23.45)) * math.sin(B)) # radians

    # Solar Noon (Dhuhr) in hours
    solar_noon = 12.0 + (tz * 15.0 - lng) / 15.0 - (EoT / 60.0)

    # Method Fajr and Isha angles
    if method == "Makkah":
        fajr_angle = 18.5
        isha_angle = 19.0
    elif method == "Egypt":
        fajr_angle = 19.5
        isha_angle = 17.5
    else: # MWL / Gulf
        fajr_angle = 18.0
        isha_angle = 17.0

    lat_rad = math.radians(lat)

    # Helper for hour angle
    def hour_angle(alt_deg):
        alt_rad = math.radians(alt_deg)
        val = (math.sin(alt_rad) - math.sin(lat_rad) * math.sin(delta)) / (math.cos(lat_rad) * math.cos(delta))
        val = max(-1.0, min(1.0, val))
        return math.degrees(math.acos(val)) / 15.0

    # Sunrise & Sunset (center of sun -0.833 deg)
    h_sun = hour_angle(-0.833)
    t_sunrise = solar_noon - h_sun
    t_sunset = solar_noon + h_sun

    # Fajr
    h_fajr = hour_angle(-fajr_angle)
    t_fajr = solar_noon - h_fajr

    # Isha
    h_isha = hour_angle(-isha_angle)
    t_isha = solar_noon + h_isha

    # Asr (Shafi'i: shadow length = object + noon shadow)
    noon_shadow = math.tan(abs(lat_rad - delta))
    asr_alt = math.degrees(math.atan(1.0 / (1.0 + noon_shadow)))
    h_asr = hour_angle(asr_alt)
    t_asr = solar_noon + h_asr

    # Dhuhr is noon + 2 min buffer
    t_dhuhr = solar_noon + 2.0 / 60.0
    # Maghrib is sunset + 2 min buffer
    t_maghrib = t_sunset + 2.0 / 60.0

    def to_time_str(hour_val):
        h = int(hour_val)
        m = int(round((hour_val - h) * 60))
        if m >= 60:
            h += 1
            m -= 60
        h = h % 24
        if clean_lang == "ar":
            period = "ص" if h < 12 else "م"
        else:
            period = "AM" if h < 12 else "PM"
        disp_h = h if h <= 12 else h - 12
        if disp_h == 0:
            disp_h = 12
        return f"{disp_h:02d}:{m:02d} {period}", f"{h:02d}:{m:02d}"

    fajr_str, fajr_24 = to_time_str(t_fajr)
    sunrise_str, sunrise_24 = to_time_str(t_sunrise)
    dhuhr_str, dhuhr_24 = to_time_str(t_dhuhr)
    asr_str, asr_24 = to_time_str(t_asr)
    maghrib_str, maghrib_24 = to_time_str(t_maghrib)
    isha_str, isha_24 = to_time_str(t_isha)

    # Determine next prayer and countdown
    now = datetime.now()
    now_min = now.hour * 60 + now.minute

    def get_pname(pkey):
        return PRAYER_LOCALIZED_NAMES.get(pkey, {}).get(clean_lang, PRAYER_LOCALIZED_NAMES[pkey]["ar"])

    prayers_list = [
        (get_pname("fajr"), int(fajr_24.split(":")[0]) * 60 + int(fajr_24.split(":")[1]), fajr_str),
        (get_pname("sunrise"), int(sunrise_24.split(":")[0]) * 60 + int(sunrise_24.split(":")[1]), sunrise_str),
        (get_pname("dhuhr"), int(dhuhr_24.split(":")[0]) * 60 + int(dhuhr_24.split(":")[1]), dhuhr_str),
        (get_pname("asr"), int(asr_24.split(":")[0]) * 60 + int(asr_24.split(":")[1]), asr_str),
        (get_pname("maghrib"), int(maghrib_24.split(":")[0]) * 60 + int(maghrib_24.split(":")[1]), maghrib_str),
        (get_pname("isha"), int(isha_24.split(":")[0]) * 60 + int(isha_24.split(":")[1]), isha_str)
    ]

    next_prayer = None
    countdown_str = ""
    for name, p_min, p_disp in prayers_list:
        if p_min > now_min:
            diff = p_min - now_min
            h_diff = diff // 60
            m_diff = diff % 60
            next_prayer = {"name": name, "time": p_disp, "diff_min": diff}
            if clean_lang == "ar":
                countdown_str = f"متبقي {h_diff} ساعة و {m_diff} دقيقة" if h_diff > 0 else f"متبقي {m_diff} دقيقة"
            else:
                countdown_str = f"in {h_diff}h {m_diff}m" if h_diff > 0 else f"in {m_diff}m"
            break

    if not next_prayer:
        # Next prayer is Tomorrow's Fajr
        diff = (1440 - now_min) + prayers_list[0][1]
        h_diff = diff // 60
        m_diff = diff % 60
        fajr_name = get_pname("fajr")
        tomorrow_suffix = " (غداً)" if clean_lang == "ar" else " (Tomorrow)"
        next_prayer = {"name": f"{fajr_name}{tomorrow_suffix}", "time": fajr_str, "diff_min": diff}
        if clean_lang == "ar":
            countdown_str = f"متبقي {h_diff} ساعة و {m_diff} دقيقة"
        else:
            countdown_str = f"in {h_diff}h {m_diff}m"

    return {
        "city": city_name,
        "date_gregorian": target_date.strftime("%Y-%m-%d"),
        "fajr": fajr_str,
        "sunrise": sunrise_str,
        "dhuhr": dhuhr_str,
        "asr": asr_str,
        "maghrib": maghrib_str,
        "isha": isha_str,
        "next_prayer": next_prayer,
        "countdown_text": countdown_str,
        "all_cities": list(CITIES_DB.keys())
    }
