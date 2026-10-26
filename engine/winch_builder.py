import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/winch-pull-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "a7c8e9f0b1d2c3e4f5a6b7c8d9e0f1a2").strip()
CUSTOM_WINCH = os.environ.get("CUSTOM_WINCH", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_winches.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (Vehicle / Winch Model Name, Loaded GVWR lbs, Rec Winch lbs, Max Amp Draw 12V, Rope Dia Inches, Min Battery CCA)
SEED_WINCHES = [
    ("Warn VR EVO 10-S (10,000 lb Synthetic Rope Winch)", 6400, 10000, 358, "3/8-Inch UHMWPE", 650),
    ("Warn VR EVO 12-S (12,000 lb Synthetic Rope Winch)", 7800, 12000, 396, "3/8-Inch UHMWPE", 750),
    ("Warn Zeon 10-S Platinum (10,000 lb Extreme Duty)", 6500, 10000, 409, "3/8-Inch Spydura", 750),
    ("Badland Apex 12,000 lb Waterproof Synthetic Winch", 7800, 12000, 420, "3/8-Inch Synthetic", 750),
    ("Badland ZXR 9,500 lb Truck & SUV Recovery Winch", 6000, 9500, 365, "3/8-Inch Wire/Syn", 650),
    ("Smittybilt X2O GEN3 10,000 lb Waterproof Winch", 6400, 10000, 380, "3/8-Inch Synthetic", 650),
    ("Smittybilt X2O GEN3 12,000 lb Synthetic Rope Winch", 7800, 12000, 415, "3/8-Inch Synthetic", 750),
    ("Superwinch Tiger Shark 9500SR & 11500SR Winch", 7200, 11500, 390, "3/8-Inch Synthetic", 700),
    ("ComeUp Seal Gen2 9.5rs & 12.5rs Off-Road Winch", 7600, 12500, 410, "3/8-Inch Synthetic", 750),
    ("Mile Marker SEC12 (12,000 lb) Sealed Electric Winch", 7800, 12000, 405, "3/8-Inch Synthetic", 750),
    ("Rough Country Pro Series 9500S & 12000S Winch", 7500, 12000, 410, "3/8-Inch Synthetic", 700),
    ("Openroad Panther Series 13,500 lb Synthetic Winch", 8500, 13500, 435, "3/8-Inch Synthetic", 800),
    ("Jeep Wrangler JLU 4-Door Rubicon (6,100 lb GVWR)", 6100, 10000, 365, "3/8-Inch Synthetic", 650),
    ("Jeep Wrangler 2-Door Willys / Sport (5,200 lb GVWR)", 5200, 9500, 350, "3/8-Inch Synthetic", 650),
    ("Jeep Gladiator Rubicon / Mojave (6,500 lb Overland)", 6500, 12000, 396, "3/8-Inch Synthetic", 750),
    ("Ford Bronco Badlands / Wildtrak Sasquatch 4-Door", 6300, 10000, 365, "3/8-Inch Synthetic", 700),
    ("Toyota Tacoma TRD Pro & Overland Rig (6,200 lb GVWR)", 6200, 10000, 365, "3/8-Inch Synthetic", 700),
    ("Toyota 4Runner TRD Off-Road & Overland Build", 6300, 10000, 365, "3/8-Inch Synthetic", 700),
    ("Toyota Land Cruiser 250 / Lexus GX 550 Overtrail", 6900, 12000, 396, "3/8-Inch Synthetic", 750),
    ("Ford F-150 Tremor & Raptor Off-Road Truck", 7300, 12000, 410, "3/8-Inch Synthetic", 750),
    ("Ford F-250 / F-350 Super Duty Tremor (10,000 lb GVWR)", 10000, 16500, 465, "7/16-Inch Synthetic", 850),
    ("Ram 2500 Power Wagon 4x4 Factory Winch Sizing", 8565, 12500, 420, "3/8-Inch Synthetic", 800),
    ("Chevrolet Silverado 1500 ZR2 Bison & Colorado ZR2", 7100, 12000, 396, "3/8-Inch Synthetic", 750),
    ("Polaris RZR Pro R / Turbo R 4-Seat UTV (2,600 lb)", 2600, 4500, 210, "1/4-Inch Synthetic", 450),
    ("Can-Am Maverick X3 Max & Defender HD10 UTV", 2800, 5000, 225, "1/4-Inch Synthetic", 450),
    ("Honda Pioneer 1000-5 & Talon 1000R Side-by-Side", 2500, 4500, 210, "1/4-Inch Synthetic", 450),
    ("Polaris Ranger XP 1000 NorthStar Crew Hunting UTV", 3100, 6000, 250, "1/4-Inch Synthetic", 500),
    ("20-Foot Car Hauler Flatbed Trailer Winch Sizing", 6500, 9500, 355, "3/8-Inch Synthetic", 650),
    ("Enclosed Race Car & Dead-Vehicle Trailer Winch", 5500, 5500, 240, "1/4-Inch Synthetic", 550),
    ("Warn Axon 55-S & SuperATV Black Ops 6000 lb UTV", 3000, 5500, 235, "1/4-Inch Synthetic", 500)
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=6500.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_winch_queries():
    discovered = []
    seeds = [
        "what size winch for ",
        "warn vr evo ",
        "badland apex 12000 ",
        "winch calculator for "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        is_utv = any(k in cleaned for k in ["utv", "atv", "rzr", "ranger", "maverick", "4500", "5000"])
                        if is_utv:
                            discovered.append((cleaned.title(), 2600, 4500, 210, "1/4-Inch Synthetic", 450))
                        else:
                            discovered.append((cleaned.title(), 6500, 10000, 380, "3/8-Inch Synthetic", 700))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_winch_data(winch_tuple):
    """Mesin Fisika Recovery Winch SAE J706 & U.S. Army FM 20-22 (100% bebas gagal)."""
    item_name, gvwr_lbs, rec_winch_lbs, max_amps, rope_spec, min_cca = winch_tuple

    # Rumus Dasar Minimum Winch Capacity = 1.5x Loaded GVWR
    min_15x_pull = int(round(gvwr_lbs * 1.5, -2))
    # Drum Layer Derating: Lapisan ke-1 (Bare Drum) = 100%, Lapisan ke-4 (Outer Wrap) kehilangan ~33% (tersisa 67%)
    layer_4_pull_lbs = int(round(rec_winch_lbs * 0.67, -2))
    # Double-Line Pull dengan Snatch Ring / Pulley Block = 2.0x kapasitas (dikurangi ~8% gesekan ring)
    snatch_double_pull_lbs = int(round(rec_winch_lbs * 1.85, -2))

    # Ukuran kabel baterai 12V untuk arus puncak 200A-450A
    cable_awg = "2 AWG Pure Copper" if max_amps >= 340 else "4 AWG / 6 AWG Pure Copper"
    shackle_wll = int(round(rec_winch_lbs * 2.0, -3))

    return {
        "winch_name": item_name,
        "seo_title": f"{item_name} Winch Pull Capacity, Drum Layer & Amp Calculator (2026)",
        "meta_description": f"Calculate exact 1.5x GVWR winch capacity ({min_15x_pull:,} lbs), mud/slope bog resistance, outer drum layer pull ({layer_4_pull_lbs:,} lbs), and 12V {max_amps}A battery sizing for {item_name}.",
        "specs": {
            "loaded_gvwr_lbs": gvwr_lbs,
            "min_15x_capacity_lbs": min_15x_pull,
            "recommended_winch_lbs": rec_winch_lbs,
            "outer_layer4_pull_lbs": layer_4_pull_lbs,
            "double_line_snatch_lbs": snatch_double_pull_lbs,
            "max_amp_draw_12v": max_amps,
            "min_battery_cca": min_cca,
            "rope_diameter_spec": rope_spec,
            "power_cable_awg": cable_awg
        },
        "recovery_verdict": f"For {item_name} (~{gvwr_lbs:,} lbs loaded trail weight), the SAE J706 1.5x baseline requires at least {min_15x_pull:,} lbs of pulling force—making a {rec_winch_lbs:,} lb winch ({rope_spec}) the optimal match. Because a {rec_winch_lbs:,} lb winch loses ~11% mechanical leverage per rope layer wrapped on the drum (dropping to just {layer_4_pull_lbs:,} lbs on the 4th outer wrap), carrying an aluminum Snatch Ring & Soft Shackle kit restores {snatch_double_pull_lbs:,} lbs of double-line pulling force while cutting peak {max_amps}A 12V battery draw nearly in half.",
        "hardware_bundle": [
            {
                "badge": f"{rec_winch_lbs:,} lb Synthetic Winch",
                "title": f"{rec_winch_lbs:,} lb IP68 Waterproof 12V Electric Winch with {rope_spec} Rope & Wireless Remote",
                "price_range": "$349 - $1,199",
                "amazon_query": f"{rec_winch_lbs} lb Synthetic Rope Winch Waterproof 12V Warn Badland",
                "winch_note": f"Provides {rec_winch_lbs:,} lbs Layer-1 line pull with 3-stage planetary gears and automatic load-holding cone brake."
            },
            {
                "badge": "2x Pull Snatch Ring Kit",
                "title": f"CNC Aluminum Winch Snatch Recovery Ring + {shackle_wll * 2:,} lb MBS UHMWPE Soft Shackles (2-Pack)",
                "price_range": "$69 - $159",
                "amazon_query": "Winch Snatch Recovery Ring Soft Shackle Kit Off Road Synthetic Rope",
                "winch_note": f"Rigging a double-line pull boosts effective pulling power to {snatch_double_pull_lbs:,} lbs and prevents 400A winch motor stalling in axle-deep mud."
            },
            {
                "badge": f"{min_cca}+ CCA AGM Battery",
                "title": f"Deep-Cycle Dual-Purpose AGM Off-Road Battery ({min_cca}+ CCA) + 500A Master Winch Cut-Off Switch",
                "price_range": "$189 - $369",
                "amazon_query": "Odyssey Optima YellowTop AGM Battery 500A Winch Cutoff Switch",
                "winch_note": f"Full-load winching draws {max_amps} Amps DC (3x more than your alternator produces at idle); high Reserve Capacity AGM prevents voltage drop below 10.5V."
            },
            {
                "badge": "Winch Plate & Fairlead",
                "title": "Heavy-Duty 1/4\" Steel Winch Mounting Plate / Cradle + Billet Hawse Fairlead & Hook Stopper",
                "price_range": "$89 - $289",
                "amazon_query": "Heavy Duty Winch Mounting Plate Bracket Billet Hawse Fairlead",
                "winch_note": "Standard 10\" × 4.5\" bolt pattern mounts directly to frame horns without flexing under off-angle recovery pulls."
            }
        ],
        "field_checklist": [
            f"Keep the engine running at 1,500–2,000 RPM while winching and stick to 30-to-45 second pulls followed by 2 minutes of motor cooling; drawing {max_amps} Amps continuously overheats series-wound copper windings.",
            f"Unspool enough synthetic rope to reach Layer 1 or Layer 2 on the drum whenever you are bogged deep: your {rec_winch_lbs:,} lb winch only pulls {layer_4_pull_lbs:,} lbs on the outermost 4th layer!",
            "Use a Snatch Ring & Tree Saver Strap to rig a 2:1 Double-Line Pull back to your bumper recovery points whenever mud reaches your differentials or slope exceeds 25 degrees.",
            "Install a 500-Amp Manual Master Disconnect Switch on the positive winch power lead near the battery so a front-end collision can never short-circuit the unfused 2 AWG cable."
        ],
        "faqs": [
            {
                "q": f"How do I calculate the right winch size for {item_name} ({gvwr_lbs:,} lbs)?",
                "a": f"Multiply your fully loaded trail GVWR ({gvwr_lbs:,} lbs including armor, roof rack, fuel, and gear) by 1.5 to get a {min_15x_pull:,} lb minimum rating, then round up to a {rec_winch_lbs:,} lb winch to compensate for outer-drum layer power loss."
            },
            {
                "q": f"How much pulling power does a {rec_winch_lbs:,} lb winch lose on the outer drum layers?",
                "a": f"Winches are rated only on Layer 1 (the first wrap touching bare metal). Every layer of rope increases effective drum diameter, reducing torque by ~11% per wrap: Layer 1 = {rec_winch_lbs:,} lbs, Layer 2 = {int(round(rec_winch_lbs*0.89, -1)):,} lbs, Layer 3 = {int(round(rec_winch_lbs*0.78, -1)):,} lbs, and Layer 4 = {layer_4_pull_lbs:,} lbs."
            },
            {
                "q": f"How many amps does a {rec_winch_lbs:,} lb winch draw on a 12V battery?",
                "a": f"At no-load line spooling it draws ~65 Amps, rising to {max_amps} Amps DC at full {rec_winch_lbs:,} lb stall load. Always pair it with a {min_cca}+ CCA Deep-Cycle AGM battery and {cable_awg} battery cables."
            }
        ]
    }


def generate_winch_data(winch_tuple):
    if not GEMINI_API_KEY:
        return build_deterministic_winch_data(winch_tuple)

    item_name, gvwr_lbs, rec_winch_lbs, max_amps, rope_spec, min_cca = winch_tuple
    det_fallback = build_deterministic_winch_data(winch_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified I4WDTA (International 4-Wheel Drive Trainers Association) Master Recovery Instructor & Automotive Electrical Engineer. Create an accurate 2026 winch line-pull capacity (SAE J706 / FM 20-22 mud & slope physics), drum layer derating, and 12V battery amp sizing guide for: "{item_name}".
Baseline specs: Loaded GVWR={gvwr_lbs} lbs, 1.5x Min Pull={sp['min_15x_capacity_lbs']} lbs, Recommended Winch={rec_winch_lbs} lbs ({rope_spec}), Outer Layer-4 Pull={sp['outer_layer4_pull_lbs']} lbs, 2x Snatch Pull={sp['double_line_snatch_lbs']} lbs, Max 12V Draw={max_amps}A ({min_cca} CCA Battery, {sp['power_cable_awg']}).
Return ONLY a valid JSON object matching this exact schema:
{{
  "winch_name": "{item_name}",
  "seo_title": "{item_name} Winch Pull Capacity, Drum Layer & Amp Calculator (2026)",
  "meta_description": "Calculate exact 1.5x GVWR winch capacity, mud/slope mire resistance, outer drum layer derating, and 12V battery amp draw for {item_name}.",
  "specs": {{
    "loaded_gvwr_lbs": {gvwr_lbs},
    "min_15x_capacity_lbs": {sp['min_15x_capacity_lbs']},
    "recommended_winch_lbs": {rec_winch_lbs},
    "outer_layer4_pull_lbs": {sp['outer_layer4_pull_lbs']},
    "double_line_snatch_lbs": {sp['double_line_snatch_lbs']},
    "max_amp_draw_12v": {max_amps},
    "min_battery_cca": {min_cca},
    "rope_diameter_spec": "{rope_spec}",
    "power_cable_awg": "{sp['power_cable_awg']}"
  }},
  "recovery_verdict": "3-sentence technical summary stating loaded GVWR, 1.5x winch rating, Layer-1 vs Layer-4 drum derating, 2x snatch ring advantage, and peak 12V amp draw.",
  "hardware_bundle": [
    {{
      "badge": "{rec_winch_lbs} lb Synthetic Winch",
      "title": "{rec_winch_lbs} lb Waterproof 12V Electric Winch with {rope_spec} Rope",
      "price_range": "$349 - $1,199",
      "amazon_query": "{rec_winch_lbs} lb Synthetic Rope Winch Waterproof 12V",
      "winch_note": "1-sentence planetary gear and line pull note"
    }},
    {{
      "badge": "2x Snatch Ring & Shackles",
      "title": "CNC Aluminum Winch Snatch Recovery Ring + UHMWPE Soft Shackles Kit",
      "price_range": "$69 - $159",
      "amazon_query": "Winch Snatch Recovery Ring Soft Shackle Kit",
      "winch_note": "1-sentence 2:1 mechanical advantage and amp reduction note"
    }},
    {{
      "badge": "{min_cca}+ CCA AGM Battery",
      "title": "Deep-Cycle AGM Winching Battery ({min_cca}+ CCA) + 500A Master Cut-Off Switch",
      "price_range": "$189 - $369",
      "amazon_query": "AGM Deep Cycle Battery 500A Winch Disconnect Switch",
      "winch_note": "1-sentence {max_amps}A peak draw and reserve capacity note"
    }},
    {{
      "badge": "Winch Plate & Fairlead",
      "title": "Heavy-Duty Steel Winch Mounting Plate + Billet Aluminum Hawse Fairlead",
      "price_range": "$89 - $289",
      "amazon_query": "Heavy Duty Winch Mounting Plate Hawse Fairlead",
      "winch_note": "1-sentence 10x4.5 bolt pattern and synthetic rope protection note"
    }}
  ],
  "field_checklist": [
    "Step 1 regarding duty cycle (45s pull / 2m rest) and 1,800 RPM engine idle",
    "Step 2 regarding unspooling to Layer 1/2 to avoid 33% outer drum power loss",
    "Step 3 regarding 2:1 snatch ring double-line rigging in axle-deep mud",
    "Step 4 regarding 500A battery disconnect switch safety"
  ],
  "faqs": [
    {{"q": "What size winch do I need for {item_name}?", "a": "Exact 1.5x GVWR calculation and mud/armor buffer."}},
    {{"q": "Why does my {rec_winch_lbs} lb winch stall when the drum is full of rope?", "a": "Exact Layer 1 through Layer 4 drum diameter torque loss numbers."}},
    {{"q": "What battery and wire size do I need for a {rec_winch_lbs} lb winch?", "a": "Exact peak amps, CCA, reserve minutes, and AWG copper cable."}}
  ]
}}
"""

    for model_id in ["gemini-2.5-flash", "gemini-2.0-flash"]:
        try:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                raw_text = re.sub(r"\s*```$", "", raw_text)
                parsed = json.loads(raw_text)
                if "specs" in parsed and "hardware_bundle" in parsed:
                    return parsed
        except Exception as e:
            print(f"[WARN] Gemini ({model_id}) notice for '{item_name}': {e}")

    return det_fallback


def build_winch_html_page(data, slug, mon_cfg):
    winch_name = data.get("winch_name", "4x4 Recovery Winch")
    sp = data.get("specs", {})
    gvwr = int(safe_float(sp.get("loaded_gvwr_lbs", 6500), 6500))
    min_15x = int(safe_float(sp.get("min_15x_capacity_lbs", int(gvwr * 1.5)), 9750))
    rec_winch = int(safe_float(sp.get("recommended_winch_lbs", 12000), 12000))
    layer4_pull = int(safe_float(sp.get("outer_layer4_pull_lbs", int(rec_winch * 0.67)), 8040))
    double_pull = int(safe_float(sp.get("double_line_snatch_lbs", int(rec_winch * 1.85)), 22200))
    max_amps = int(safe_float(sp.get("max_amp_draw_12v", 396), 396))
    min_cca = int(safe_float(sp.get("min_battery_cca", 750), 750))
    rope_spec = sp.get("rope_diameter_spec", "3/8-Inch Synthetic")
    cable_awg = sp.get("power_cable_awg", "2 AWG Pure Copper")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "12000+lb+Synthetic+Rope+Winch+Recovery+Kit"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{winch_name} Line-Pull, Mud Resistance & Drum Layer Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "12000 lb Synthetic Rope Winch")), mon_cfg)
        bundle_html += f"""
        <div class="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col justify-between hover:border-amber-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Recovery Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$89+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-zinc-400 mt-2 leading-relaxed">🪝 {item.get('winch_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Drum Layer Derating & Amp Draw Reference Table (Layers 1 to 5)
    matrix_rows_html = ""
    for l_num, l_mult, wrap_desc in [
        (1, 1.00, "Layer 1 (Bare Drum — Max Torque)"),
        (2, 0.89, "Layer 2 (~65 ft Out — -11% Pull)"),
        (3, 0.78, "Layer 3 (~40 ft Out — -22% Pull)"),
        (4, 0.67, "Layer 4 (Outer Wrap — -33% Pull)"),
        (5, 1.85, "2:1 Snatch Ring Double-Line (Layer 2)")
    ]:
        eff_pull = int(round(rec_winch * l_mult, -1))
        est_amp = int(round(max_amps * 0.62)) if l_num == 5 else int(round(max_amps * (0.70 + 0.075 * l_num)))
        matrix_rows_html += f"""
        <tr class="border-b border-zinc-800 hover:bg-zinc-800/40">
          <td class="py-3 px-4 font-bold text-white">{wrap_desc}</td>
          <td class="py-3 px-4 font-bold text-amber-400">{eff_pull:,} lbs Max Pull</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{int(round(eff_pull * 1.85, -1)):,} lbs (w/ Snatch Ring)</td>
          <td class="py-3 px-4 text-xs text-zinc-300">~{est_amp}A @ 12V DC</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("field_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-zinc-900 border border-zinc-800 rounded-xl p-4 cursor-pointer hover:border-zinc-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-amber-500 rounded cursor-pointer winch-check">
          <span class="text-sm text-zinc-200 leading-relaxed"><strong>Recovery Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-zinc-900 border border-zinc-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-zinc-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', winch_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', winch_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-zinc-950 text-zinc-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">WINCH</span>PullIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop 4x4 Winches & Recovery Kits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-amber-500 text-zinc-950 px-3 py-1 rounded-full">{rec_winch:,} lb Winch ({rope_spec})</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Layer 4: {layer4_pull:,} lbs | 2x Snatch: {double_pull:,} lbs</span>
        <span class="text-xs font-semibold bg-zinc-800 text-zinc-300 px-3 py-1 rounded-full">Peak Draw: {max_amps}A ({min_cca}+ CCA AGM)</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', winch_name)}</h1>
      <div class="mt-4 bg-zinc-900 border-l-4 border-amber-500 p-4 rounded-r-xl text-sm text-zinc-200 leading-relaxed">
        <strong>SAE J706 & U.S. Army FM 20-22 Recovery Verdict:</strong> {data.get('recovery_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE MUD/SLOPE RESISTANCE, DRUM LAYER & SNATCH RING CALCULATOR -->
    <section class="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {winch_name} Mud, Slope & Drum Layer Calculator</h2>
      <p class="text-xs text-zinc-400 mb-6">Adjust your loaded vehicle weight, mud/bog depth, hill incline angle, and active rope drum layer to compute real-world recovery pull force required vs. available winch torque.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="wtSlider" class="text-zinc-300">Loaded Vehicle Trail Weight (GVWR + Armor + Gear lbs)</label>
              <span class="text-amber-400 font-bold"><span id="wtVal">{gvwr:,}</span> lbs</span>
            </div>
            <input id="wtSlider" type="range" min="1500" max="14000" step="250" value="{gvwr}" class="w-full accent-amber-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="mireSelect" class="block text-xs font-medium text-zinc-400 mb-1">Mud / Snow Bog Depth (FM 20-22)</label>
              <select id="mireSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="0.20">Hard Trail / Wet Grass (+20%)</option>
                <option value="1.00" selected>Tire / Hub-Deep Mud or Snow (+100%)</option>
                <option value="2.00">Fender / Frame-Deep Bog (+200%)</option>
              </select>
            </div>
            <div>
              <label for="layerSelect" class="block text-xs font-medium text-zinc-400 mb-1">Rope Layer on Winch Drum</label>
              <select id="layerSelect" class="w-full bg-zinc-950 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500">
                <option value="1.00">Layer 1 (Bare Drum - 100% Power)</option>
                <option value="0.89">Layer 2 (~65ft Out - 89% Power)</option>
                <option value="0.78" selected>Layer 3 (~40ft Out - 78% Power)</option>
                <option value="0.67">Layer 4 (Full Drum - 67% Power)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="slopeSlider" class="text-zinc-300">Recovery Incline / Hill Angle (Degrees)</label>
              <span class="text-amber-400 font-bold"><span id="slopeVal">15</span>° Slope</span>
            </div>
            <input id="slopeSlider" type="range" min="0" max="45" step="5" value="15" class="w-full accent-amber-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-zinc-950 border border-amber-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-amber-400 font-bold">Total Pull Force Needed</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="forceReqOut">0</span> <span class="text-xs font-normal text-zinc-400">lbs</span></div>
            <p id="riggingNoteOut" class="text-xs text-amber-400 font-semibold mt-1">1.5x Rule Min: {min_15x:,} lbs</p>
          </div>

          <div class="bg-zinc-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Required Winch Size</span>
            <div id="recWinchOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">{rec_winch:,} lb Winch</div>
            <p id="snatchStatusOut" class="text-xs text-zinc-300 font-semibold mt-1">Single-Line Pull OK</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-amber-950/40 border border-amber-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="winchAdviceBanner" class="text-sm text-amber-100 font-medium"></div>
        <a id="dynamicWinchBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Winch & Snatch Ring on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {winch_name} Winch, Snatch Ring & AGM Battery Bundle</h2>
        <span class="text-xs text-zinc-400">SAE J706 & IP68 Waterproof Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- DRUM LAYER DERATING MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">{winch_name} Drum Layer Derating & Snatch Ring Power Chart</h2>
      <div class="overflow-x-auto bg-zinc-900 border border-zinc-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-zinc-800 bg-zinc-950/60 text-zinc-400 uppercase text-xs">
              <th class="py-3.5 px-4">Drum Rope Layer</th>
              <th class="py-3.5 px-4 text-amber-400">Single-Line Max Pull</th>
              <th class="py-3.5 px-4 text-emerald-400">2:1 Double-Line (Snatch Ring)</th>
              <th class="py-3.5 px-4">12V Battery Amp Draw</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- RECOVERY CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">I4WDTA Safe Winching, Duty Cycle & Electrical Checklist</h2>
        <span id="winchBadge" class="text-xs font-bold bg-zinc-800 text-amber-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({winch_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500 px-4">
    <p>© {datetime.now(timezone.utc).year} WinchPullIndex. Independent 4x4 Recovery Physics & SAE J706 Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const baseRatedWinch = {rec_winch};
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const wtSlider = document.getElementById('wtSlider');
    const mireSelect = document.getElementById('mireSelect');
    const layerSelect = document.getElementById('layerSelect');
    const slopeSlider = document.getElementById('slopeSlider');
    const wtVal = document.getElementById('wtVal');
    const slopeVal = document.getElementById('slopeVal');
    const forceReqOut = document.getElementById('forceReqOut');
    const riggingNoteOut = document.getElementById('riggingNoteOut');
    const recWinchOut = document.getElementById('recWinchOut');
    const snatchStatusOut = document.getElementById('snatchStatusOut');
    const winchAdviceBanner = document.getElementById('winchAdviceBanner');
    const dynamicWinchBtn = document.getElementById('dynamicWinchBtn');

    function recalculateWinch() {{
      const wt = parseInt(wtSlider.value, 10);
      const mireMult = parseFloat(mireSelect.value);
      const layerMult = parseFloat(layerSelect.value);
      const deg = parseInt(slopeSlider.value, 10);

      wtVal.textContent = wt.toLocaleString();
      slopeVal.textContent = deg;

      const rad = (deg * Math.PI) / 180.0;
      const slopeForce = wt * Math.sin(rad);
      const mireForce = wt * mireMult;
      const rollingDrag = wt * 0.10;
      const totalPullRequired = Math.round(rollingDrag + mireForce + slopeForce);

      const min15x = Math.round((wt * 1.5) / 500) * 500;
      let stdWinchTier = 4500;
      if (min15x <= 5000) stdWinchTier = 5000;
      else if (min15x <= 9500) stdWinchTier = 9500;
      else if (min15x <= 10500) stdWinchTier = 10000;
      else if (min15x <= 12500) stdWinchTier = 12000;
      else stdWinchTier = 13500;

      const availSingleLineOnLayer = Math.round(stdWinchTier * layerMult);
      const availDoubleLineOnLayer = Math.round(availSingleLineOnLayer * 1.85);

      forceReqOut.textContent = totalPullRequired.toLocaleString();
      riggingNoteOut.textContent = `Layer Avail: ${{availSingleLineOnLayer.toLocaleString()}} lbs`;
      recWinchOut.textContent = `${{stdWinchTier.toLocaleString()}} lb Winch`;

      if (totalPullRequired <= availSingleLineOnLayer) {{
        snatchStatusOut.textContent = "✅ Single-Line Pull OK";
        snatchStatusOut.className = "text-xs text-emerald-400 font-semibold mt-1";
      }} else if (totalPullRequired <= availDoubleLineOnLayer) {{
        snatchStatusOut.textContent = `⚠️ Rig 2:1 Snatch Ring (${{availDoubleLineOnLayer.toLocaleString()}} lb cap)`;
        snatchStatusOut.className = "text-xs text-amber-400 font-bold mt-1";
      }} else {{
        snatchStatusOut.textContent = "🚨 Dig Out Mud + Rig 2:1 Snatch Block!";
        snatchStatusOut.className = "text-xs text-red-400 font-bold mt-1";
      }}

      winchAdviceBanner.innerHTML = `🪝 <strong>FM 20-22 Recovery Spec:</strong> Extracting a ${{wt.toLocaleString()}} lb rig on a ${{deg}}° slope requires <strong>${{totalPullRequired.toLocaleString()}} lbs of line pull</strong>. Install a <strong>${{stdWinchTier.toLocaleString()}} lb Synthetic Rope Winch</strong> + <strong>CNC Snatch Recovery Ring & Soft Shackles</strong>.`;
      dynamicWinchBtn.href = `https://${{amzDomain}}/s?k=${{stdWinchTier}}+lb+Synthetic+Rope+Winch+Snatch+Recovery+Ring+Soft+Shackle&tag=${{amzTag}}`;
    }}

    wtSlider.addEventListener('input', recalculateWinch);
    mireSelect.addEventListener('change', recalculateWinch);
    layerSelect.addEventListener('change', recalculateWinch);
    slopeSlider.addEventListener('input', recalculateWinch);
    recalculateWinch();

    const checks = document.querySelectorAll('.winch-check');
    const badge = document.getElementById('winchBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "12000+lb+Synthetic+Rope+Winch+Recovery+Kit"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-zinc-900 border border-zinc-800 hover:border-amber-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-amber-500 text-zinc-950 px-2.5 py-0.5 rounded">{item.get('winch_lbs', 12000):,} lb Winch</span>
            <span class="text-xs text-zinc-400">Layer 4: {item.get('layer4_lbs', 8040):,} lbs | {item.get('amps', 396)}A</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-amber-400 transition">{item['winch_name']}</h2>
          <p class="text-xs text-zinc-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-amber-400">Calculate Mud Pull & Drum Derating →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WinchPullIndex — 4x4 Truck, Jeep & UTV Winch Pull Capacity & Drum Layer Calculator (2026)</title>
  <meta name="description" content="Calculate exact 1.5x GVWR winch capacity, mud and slope recovery resistance, outer drum layer torque loss, and 12V battery amp draw for Warn, Badland Apex, Smittybilt, Jeep Wrangler, Bronco, Tacoma, and UTVs.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="WinchPullIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-zinc-950 text-zinc-100 min-h-screen flex flex-col">
  <header class="border-b border-zinc-800 bg-zinc-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-amber-500 text-zinc-950 px-2 py-0.5 rounded font-black">WINCH</span>PullIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-amber-500 hover:bg-amber-400 text-zinc-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop 4x4 Winches & Recovery Kits →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">4x4 Winch Pull Capacity, Mud Resistance & Drum Layer Database</h1>
      <p class="text-zinc-400 mt-3 text-base sm:text-lg">Select your 4x4 rig, UTV, trailer, or winch model below to calculate real-world mud/incline pull requirements, outer drum wrap torque loss, and 12V AGM battery amp draw.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search vehicle or winch (e.g. Warn VR EVO 10-S, Badland Apex 12000, Jeep Wrangler, Bronco, Tacoma, RZR...)" class="w-full bg-zinc-900 border border-zinc-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-amber-500">
      </div>
    </div>

    <div id="winchGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-zinc-800 py-8 text-center text-xs text-zinc-500">
    <p>© {datetime.now(timezone.utc).year} WinchPullIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('winchGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>WinchPullIndex 4x4 Recovery & Winch Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive 4x4 Truck, Jeep & UTV Winch Pull Capacity & Drum Layer Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_WINCH:
        candidates.append((CUSTOM_WINCH.strip(), 6500, 12000, 396, "3/8-Inch Synthetic", 750))
    candidates.extend(SEED_WINCHES)
    candidates.extend(discover_google_winch_queries())

    new_urls = []
    count = 0

    for winch_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        w_name = winch_tuple[0]
        slug = slugify(f"{w_name}-winch-pull-capacity-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating 4x4 winch pull & drum layer calculator for: {w_name}...")
        try:
            data = generate_winch_data(winch_tuple)
            build_winch_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "winch_name": data.get("winch_name", w_name),
                "slug": slug,
                "title": data.get("seo_title", f"{w_name} Winch Calculator"),
                "description": data.get("meta_description", ""),
                "winch_lbs": int(safe_float(sp.get("recommended_winch_lbs", winch_tuple[2]), winch_tuple[2])),
                "layer4_lbs": int(safe_float(sp.get("outer_layer4_pull_lbs", int(winch_tuple[2] * 0.67)), 8040)),
                "amps": int(safe_float(sp.get("max_amp_draw_12v", winch_tuple[3]), winch_tuple[3])),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] Failed building {w_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new 4x4 winch pull calculator pages.")


if __name__ == "__main__":
    main()
