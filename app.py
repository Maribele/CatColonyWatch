import hashlib
import json
import os
import re
import sqlite3
from datetime import date, datetime, time
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="CatColonyWatch", page_icon="🐾", layout="centered")


# Hide Streamlit keyboard-submit helper text (e.g. “Press Enter to apply/submit”) globally.
st.markdown(
    """
    <style>
    [data-testid="InputInstructions"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

APP_VERSION = "0.3"
APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "catcolonywatch.db"
DEFAULT_MODEL_ID = "gemma3:4b"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")

SEX_OPTIONS = ["Unknown", "Female", "Male"]
AGE_OPTIONS = ["Unknown", "Kitten", "Young", "Adult", "Senior"]
YES_NO_UNKNOWN = ["Unknown", "Yes", "No"]
FOLLOW_UP_STATUS_OPTIONS = [
    "Pending / not decided",
    "Decision made",
    "In progress",
    "Action completed",
    "No action needed",
]
WEATHER_OPTIONS = [
    "Not recorded", "Clear", "Cloudy", "Rain",
    "Wind", "Hot", "Cold", "Other"
]

SYSTEM_PROMPT = """
You are a field-note structuring assistant for community-cat colony volunteers.

Your task is ONLY to transform the volunteer's field observations into a concise,
factual and structured record.

Rules:
- Never diagnose.
- Never assess medical urgency.
- Never recommend treatment.
- Never infer emotions, intentions, diseases, causes, ownership, sex, age,
  reproductive status, or relationships unless the observer explicitly stated them.
- Separate direct observations from uncertain or interpretive statements.
- Preserve uncertainty using wording such as "observer reports..." or "uncertain".
- Do not invent missing information.
- Keep biodiversity observations factual.
- Do not turn absence of observation into evidence that something did not happen.
- A "follow_up_flag" is NOT a diagnosis or triage decision. It is only an objective
  item the volunteer may wish to check again or share with the relevant
  colony-management or veterinary team.
- Return VALID JSON only.
- Use exactly these top-level keys:

{
  "observed_facts": ["..."],
  "individuals": [
    {
      "identifier": "...",
      "observations": ["..."]
    }
  ],
  "biodiversity": ["..."],
  "environment": ["..."],
  "uncertain_or_interpretive_statements": ["..."],
  "follow_up_flags": ["..."]
}
""".strip()


# -------------------- DATABASE --------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _column_names(conn, table_name):
    return {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _add_column_if_missing(conn, table_name, column_name, definition):
    if column_name not in _column_names(conn, table_name):
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def init_db():
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colony TEXT,
            name TEXT NOT NULL,
            sex TEXT,
            estimated_age TEXT,
            sterilised TEXT,
            ear_tip TEXT,
            identification TEXT,
            coat_description TEXT,
            health_notes TEXT,
            general_notes TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    _add_column_if_missing(conn, "cats", "follow_up_text", "TEXT")
    _add_column_if_missing(
        conn,
        "cats",
        "follow_up_status",
        "TEXT DEFAULT 'Pending / not decided'"
    )
    _add_column_if_missing(conn, "cats", "follow_up_date", "TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_date TEXT,
            colony TEXT,
            observer TEXT,
            observation_minutes INTEGER,
            weather TEXT,
            cats_seen INTEGER,
            known_cats INTEGER,
            unknown_cats INTEGER,
            kittens_seen INTEGER,
            food_water TEXT,
            feeding_point TEXT,
            biodiversity_notes TEXT,
            raw_notes TEXT,
            structured_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    _add_column_if_missing(conn, "visits", "start_time", "TEXT")
    _add_column_if_missing(conn, "visits", "end_time", "TEXT")
    _add_column_if_missing(conn, "visits", "duration_minutes", "INTEGER")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visit_cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER NOT NULL,
            cat_id INTEGER NOT NULL,
            seen INTEGER DEFAULT 1,
            visit_notes TEXT,
            FOREIGN KEY (visit_id) REFERENCES visits(id) ON DELETE CASCADE,
            FOREIGN KEY (cat_id) REFERENCES cats(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS visit_unknown_cats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER NOT NULL,
            temporary_label TEXT,
            sex TEXT,
            estimated_age TEXT,
            coat_description TEXT,
            notes TEXT,
            FOREIGN KEY (visit_id) REFERENCES visits(id) ON DELETE CASCADE
        )
        """
    )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_cats_name ON cats(name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cats_colony ON cats(colony)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_visits_date ON visits(visit_date)")
    conn.commit()
    conn.close()


def add_cat(data):
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO cats (
            colony, name, sex, estimated_age, sterilised, ear_tip,
            identification, coat_description, health_notes, general_notes,
            follow_up_text, follow_up_status, follow_up_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["colony"], data["name"], data["sex"], data["estimated_age"],
            data["sterilised"], data["ear_tip"], data["identification"],
            data["coat_description"], data["health_notes"], data["general_notes"],
            data["follow_up_text"], data["follow_up_status"], data["follow_up_date"],
        ),
    )
    cat_id = cur.lastrowid
    conn.commit()
    conn.close()
    return cat_id


def get_cats(active_only=True):
    conn = get_connection()
    query = "SELECT * FROM cats"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY name COLLATE NOCASE, colony COLLATE NOCASE"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_cat(cat_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM cats WHERE id = ?", (cat_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_cat(cat_id, data):
    conn = get_connection()
    conn.execute(
        """
        UPDATE cats
        SET colony=?, name=?, sex=?, estimated_age=?, sterilised=?, ear_tip=?,
            identification=?, coat_description=?, health_notes=?, general_notes=?,
            follow_up_text=?, follow_up_status=?, follow_up_date=?
        WHERE id=?
        """,
        (
            data["colony"], data["name"], data["sex"], data["estimated_age"],
            data["sterilised"], data["ear_tip"], data["identification"],
            data["coat_description"], data["health_notes"], data["general_notes"],
            data["follow_up_text"], data["follow_up_status"], data["follow_up_date"],
            cat_id,
        ),
    )
    conn.commit()
    conn.close()


def save_visit(
    visit, structured, selected_cat_ids, per_cat_notes,
    unknown_cat_records, food_water, feeding_point, biodiversity_notes
):
    conn = get_connection()
    cur = conn.execute(
        """
        INSERT INTO visits (
            visit_date, colony, observer, observation_minutes, weather,
            cats_seen, known_cats, unknown_cats, kittens_seen,
            food_water, feeding_point, biodiversity_notes, raw_notes,
            structured_json, start_time, end_time, duration_minutes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(visit["date"]), visit["colony"], visit["observer"],
            visit["duration_minutes"], visit["weather"], visit["cats_seen"],
            len(selected_cat_ids), len(unknown_cat_records), None,
            food_water, feeding_point, biodiversity_notes, visit["raw_notes"],
            json.dumps(structured, ensure_ascii=False) if structured else None,
            visit["start_time"], visit["end_time"], visit["duration_minutes"],
        ),
    )
    visit_id = cur.lastrowid

    for cat_id in selected_cat_ids:
        conn.execute(
            """
            INSERT INTO visit_cats
            (visit_id, cat_id, seen, visit_notes)
            VALUES (?, ?, 1, ?)
            """,
            (visit_id, cat_id, per_cat_notes.get(cat_id, "")),
        )

    for unknown in unknown_cat_records:
        conn.execute(
            """
            INSERT INTO visit_unknown_cats (
                visit_id, temporary_label, sex, estimated_age,
                coat_description, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                visit_id,
                unknown["temporary_label"],
                unknown["sex"],
                unknown["estimated_age"],
                unknown["coat_description"],
                unknown["notes"],
            ),
        )

    conn.commit()
    conn.close()
    return visit_id


def get_visits():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            visit_date, start_time, end_time, duration_minutes,
            colony, observer, cats_seen, known_cats, unknown_cats, created_at
        FROM visits
        ORDER BY visit_date DESC, start_time DESC, created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# -------------------- AI --------------------

def get_model_id():
    return os.getenv("OLLAMA_MODEL", DEFAULT_MODEL_ID).strip()


def get_ollama_models():
    """Return installed local Ollama model names. Empty list if Ollama is unavailable."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        response.raise_for_status()
        data = response.json()
        return [
            model.get("name", "")
            for model in data.get("models", [])
            if model.get("name")
        ]
    except Exception:
        return []


def ollama_is_running():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return response.ok
    except Exception:
        return False


def model_is_installed(model_id):
    installed = get_ollama_models()
    requested_base = model_id.split(":")[0]

    for installed_name in installed:
        if installed_name == model_id:
            return True
        # Ollama may report "gemma3:latest" when the requested model is "gemma3".
        if model_id == requested_base and installed_name.startswith(requested_base + ":"):
            return True

    return False


def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and last > first:
        text = text[first:last + 1]

    return json.loads(text)


def normalise_structured_record(data):
    expected_keys = [
        "observed_facts",
        "individuals",
        "biodiversity",
        "environment",
        "uncertain_or_interpretive_statements",
        "follow_up_flags",
    ]

    if not isinstance(data, dict):
        raise ValueError("AI response is not a JSON object.")

    result = {}
    for key in expected_keys:
        value = data.get(key, [])
        result[key] = value if isinstance(value, list) else []

    return result


def structure_with_gemma(ai_input):
    """Structure the visit using a local Gemma model served by Ollama."""
    model_id = get_model_id()

    if not ollama_is_running():
        raise RuntimeError(
            "Ollama is not running on this computer. Open the Ollama app, "
            "or start Ollama, then try again."
        )

    if not model_is_installed(model_id):
        raise RuntimeError(
            f"The local model '{model_id}' is not installed yet.\n\n"
            f"Run this once in Terminal:\n\nollama pull {model_id}\n\n"
            "Then try again."
        )

    payload = {
        "model": model_id,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Structure the following community-cat field record. "
                    "Use only information explicitly present.\n\n"
                    f"{ai_input}"
                ),
            },
        ],
        "options": {
            "temperature": 0.1
        },
    }

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=180,
        )
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "CatColonyWatch could not connect to Ollama. "
            "Make sure the Ollama app is open."
        ) from exc
    except requests.Timeout as exc:
        raise RuntimeError(
            "The local model took too long to answer. "
            "Try again, or use a smaller model such as gemma3:1b."
        ) from exc

    if not response.ok:
        raise RuntimeError(
            f"Ollama returned HTTP {response.status_code}.\n\n"
            f"{response.text[:700]}"
        )

    data = response.json()

    try:
        content = data["message"]["content"]
    except (KeyError, TypeError):
        raise RuntimeError(
            "Ollama returned an unexpected response format."
        )

    return normalise_structured_record(extract_json(content))


# -------------------- HELPERS --------------------

def minutes_between(start_value, end_value):
    start_dt = datetime.combine(date.today(), start_value)
    end_dt = datetime.combine(date.today(), end_value)
    return int((end_dt - start_dt).total_seconds() // 60)


def observation_datetime_is_valid(visit_date, start_value, end_value):
    duration = minutes_between(start_value, end_value)
    if duration <= 0:
        return False, "Observation end time must be later than the start time."

    end_dt = datetime.combine(visit_date, end_value)
    if end_dt > datetime.now():
        return False, "An observation cannot end in the future."

    return True, ""


def unique_cat_labels(cats):
    labels = {}
    used = set()

    for cat in cats:
        base = (cat["name"] or "Unnamed cat").strip()
        colony = (cat.get("colony") or "").strip()
        identifier = (cat.get("identification") or "").strip()

        candidates = [base]
        if colony:
            candidates.append(f"{base} · {colony}")
        if identifier:
            candidates.append(f"{base} · {colony or 'No colony'} · {identifier}")

        chosen = None
        for candidate in candidates:
            if candidate not in used:
                chosen = candidate
                break

        if chosen is None:
            n = 2
            chosen = f"{base} · record {n}"
            while chosen in used:
                n += 1
                chosen = f"{base} · record {n}"

        used.add(chosen)
        labels[chosen] = cat["id"]

    return labels


def section_list(title, items):
    st.markdown(f"#### {title}")
    if not items:
        st.caption("No items.")
        return
    for item in items:
        st.markdown(f"- {item}")


def build_ai_input(
    visit_date, start_time_value, end_time_value, colony, observer, weather,
    selected_cat_ids, per_cat_notes, unknown_cat_records, food_water,
    feeding_point, biodiversity_notes, raw_notes
):
    lines = [
        f"Visit date: {visit_date}",
        f"Observation start: {start_time_value.strftime('%H:%M')}",
        f"Observation end: {end_time_value.strftime('%H:%M')}",
        f"Colony / feeding point: {colony or 'Not recorded'}",
        f"Observer: {observer or 'Not recorded'}",
        f"Weather: {weather}",
        "",
        "KNOWN CATS OBSERVED:",
    ]

    if selected_cat_ids:
        for cat_id in selected_cat_ids:
            cat = get_cat(cat_id)
            note = per_cat_notes.get(cat_id, "").strip()
            lines.append(
                f"- {cat['name']}: {note or 'Seen; no additional individual note.'}"
            )
    else:
        lines.append("- None recorded")

    lines += ["", "UNIDENTIFIED CATS OBSERVED:"]

    if unknown_cat_records:
        for unknown in unknown_cat_records:
            details = [
                f"label={unknown['temporary_label']}",
                f"sex={unknown['sex']}",
                f"estimated_age={unknown['estimated_age']}",
            ]
            if unknown["coat_description"]:
                details.append(f"appearance={unknown['coat_description']}")
            if unknown["notes"]:
                details.append(f"notes={unknown['notes']}")
            lines.append("- " + "; ".join(details))
    else:
        lines.append("- None recorded")

    lines += [
        "",
        "COLONY CONDITIONS:",
        f"- Food and water: {food_water}",
        f"- Feeding point / shelter: {feeding_point}",
        "",
        "BIODIVERSITY / OTHER ANIMALS:",
        biodiversity_notes.strip() or "Not recorded",
        "",
        "GENERAL FIELD NOTES:",
        raw_notes.strip() or "No additional free-text notes.",
    ]

    return "\n".join(lines)


def stable_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def show_flash_message():
    message = st.session_state.pop("flash_message", None)
    if message:
        st.success(message)


def scroll_to_page_top_if_requested():
    """
    After a save + rerun, move the browser back to the top of the app.
    This avoids leaving the volunteer at the bottom of a long form.
    """
    if st.session_state.pop("scroll_to_top", False):
        components.html(
            """
            <script>
                window.parent.scrollTo({top: 0, left: 0, behavior: "instant"});
            </script>
            """,
            height=0,
            width=0,
        )


# -------------------- APP --------------------

init_db()

st.title("🐾 CatColonyWatch")
st.subheader("Observe first. Record second. Let open AI structure the notes.")

st.info(
    "An open-source field-observation tool for community-cat volunteers. "
    "The human observes the cats; the AI only helps structure what was reported."
)

local_model = get_model_id()

if ollama_is_running():
    if model_is_installed(local_model):
        st.caption(
            f"✅ Local AI ready · Ollama · Model: `{local_model}` · App v{APP_VERSION}"
        )
    else:
        st.caption(
            f"⚠️ Ollama is running, but `{local_model}` is not installed · App v{APP_VERSION}"
        )
else:
    st.caption(
        f"⚠️ Local AI offline · Open Ollama to use Gemma · App v{APP_VERSION}"
    )

show_flash_message()
scroll_to_page_top_if_requested()

tab_visit, tab_cats, tab_history = st.tabs(
    ["🌿 Field visit", "🐈 Cat database", "📚 Visit history"]
)


with tab_visit:
    with st.expander("How to use Field Visit", expanded=True):
        st.markdown(
            """
1. Go to the colony or feeding point.
2. Observe for **5–10 minutes** with as little screen use as possible.
3. Record the known and unidentified cats you actually saw.
4. Add factual notes about individuals, the colony and other animals.
5. Let Gemma structure the record.
6. Review the AI output before saving or exporting it.
            """
        )

    st.header("1. Visit details")
    col1, col2 = st.columns(2)

    with col1:
        visit_date = st.date_input(
            "Date",
            value=date.today(),
            max_value=date.today(),
            key="visit_date",
            help="Completed observations cannot be dated in the future.",
        )
        colony = st.text_input(
            "Colony / feeding point",
            placeholder="e.g. Riverside colony",
            key="visit_colony",
        )
        observer = st.text_input(
            "Observer",
            placeholder="Initials or name",
            key="visit_observer",
        )

    with col2:
        start_time_value = st.time_input(
            "Observation start",
            value=time(18, 0),
            step=300,
            key="visit_start_time",
        )
        end_time_value = st.time_input(
            "Observation end",
            value=time(18, 10),
            step=300,
            key="visit_end_time",
        )
        weather = st.selectbox(
            "Weather",
            WEATHER_OPTIONS,
            key="visit_weather",
        )

    duration_minutes = minutes_between(start_time_value, end_time_value)
    time_valid, time_error = observation_datetime_is_valid(
        visit_date, start_time_value, end_time_value
    )

    if time_valid:
        st.caption(f"Calculated observation duration: **{duration_minutes} minutes**")
    else:
        st.error(time_error)

    st.header("2. Known cats observed")
    cats = get_cats()
    cat_options = unique_cat_labels(cats)

    selected_labels = st.multiselect(
        "Which known cats did you see?",
        options=list(cat_options.keys()),
        placeholder="Select one or more registered cats",
        key="known_cats_seen",
    )
    selected_cat_ids = [cat_options[label] for label in selected_labels]

    per_cat_notes = {}
    if selected_cat_ids:
        st.markdown("#### Individual observations")
        for cat_id in selected_cat_ids:
            cat = get_cat(cat_id)
            per_cat_notes[cat_id] = st.text_area(
                f"{cat['name']} — observations during this visit",
                placeholder=(
                    "e.g. Ate for about 3 minutes; walked normally; "
                    "small scratch visible on right ear."
                ),
                key=f"cat_visit_notes_{cat_id}",
                height=90,
            )
    elif cats:
        st.caption("No known cats selected yet.")
    else:
        st.info(
            "No known cats are registered yet. Add them in the Cat database tab."
        )

    st.header("3. Unidentified / unknown cats")
    unknown_count = st.number_input(
        "How many unidentified cats do you want to record individually?",
        min_value=0,
        max_value=30,
        value=0,
        step=1,
        key="unknown_count",
    )

    unknown_cat_records = []
    for i in range(int(unknown_count)):
        with st.expander(f"Unknown cat {i + 1}", expanded=True):
            u1, u2 = st.columns(2)
            with u1:
                temporary_label = st.text_input(
                    "Temporary label",
                    value=f"Unknown {i + 1}",
                    key=f"unknown_label_{i}",
                    help=(
                        "A temporary field label for this visit. "
                        "It is not a permanent database ID."
                    ),
                )
                unknown_sex = st.selectbox(
                    "Sex", SEX_OPTIONS, key=f"unknown_sex_{i}"
                )
            with u2:
                unknown_age = st.selectbox(
                    "Estimated age", AGE_OPTIONS, key=f"unknown_age_{i}"
                )
                unknown_coat = st.text_input(
                    "Coat / identifying features",
                    placeholder="e.g. orange tabby, white chest",
                    key=f"unknown_coat_{i}",
                )

            unknown_notes = st.text_area(
                "Observed notes",
                placeholder="Only what was actually observed.",
                key=f"unknown_notes_{i}",
                height=80,
            )

            unknown_cat_records.append(
                {
                    "temporary_label": temporary_label.strip() or f"Unknown {i + 1}",
                    "sex": unknown_sex,
                    "estimated_age": unknown_age,
                    "coat_description": unknown_coat.strip(),
                    "notes": unknown_notes.strip(),
                }
            )

    st.header("4. Total cats observed during this visit")
    minimum_recorded_cats = len(selected_cat_ids) + len(unknown_cat_records)

    st.caption(
        "Count every cat you saw during the observation: known cats, unidentified cats "
        "recorded above, and any additional cats you noticed but could not identify or "
        "describe individually."
    )

    total_cats_seen = st.number_input(
        "Total cats observed during this visit",
        min_value=minimum_recorded_cats,
        value=minimum_recorded_cats,
        step=1,
        key="total_cats_seen",
        help=(
            "Example: if you selected 2 known cats, recorded 1 unidentified cat, "
            "and also saw 2 other cats briefly, enter 5."
        ),
    )

    additional_unrecorded = total_cats_seen - minimum_recorded_cats
    if additional_unrecorded > 0:
        st.caption(
            f"✓ {additional_unrecorded} additional cat(s) were observed but not "
            "recorded individually."
        )
    elif total_cats_seen > 0:
        st.caption(
            "✓ The total matches the cats recorded individually above."
        )

    st.header("5. Colony conditions")
    food_water = st.selectbox(
        "Food and water",
        [
            "Not recorded",
            "Food and water available",
            "Food available, no water observed",
            "Water available, no food observed",
            "Neither observed",
            "Other",
        ],
        key="food_water",
    )

    feeding_point = st.selectbox(
        "Feeding point / shelter condition",
        [
            "Not recorded",
            "Clean / in good condition",
            "Needs cleaning",
            "Damaged",
            "Changed or displaced",
            "Other",
        ],
        key="feeding_point",
    )

    biodiversity_notes = st.text_area(
        "Other animals / biodiversity observed",
        placeholder="e.g. 2 magpies near feeding point; 1 hedgehog seen by hedge.",
        height=90,
        key="biodiversity_notes",
    )

    st.header("6. General field notes")
    raw_notes = st.text_area(
        "What else did you observe?",
        height=200,
        placeholder=(
            "Example: One orange cat stayed near the bushes. "
            "The water bowl had been moved. "
            "Two magpies were feeding about 5 metres away."
        ),
        key="raw_notes",
    )

    st.caption(
        "Describe visible or audible facts. Avoid conclusions such as "
        "'sad', 'aggressive' or 'sick' unless you clearly mark them "
        "as your interpretation."
    )

    ai_input = build_ai_input(
        visit_date, start_time_value, end_time_value, colony, observer, weather,
        selected_cat_ids, per_cat_notes, unknown_cat_records, food_water,
        feeding_point, biodiversity_notes, raw_notes
    )

    current_input_hash = stable_hash(ai_input)

    if (
        st.session_state.get("structured_input_hash")
        and st.session_state.get("structured_input_hash") != current_input_hash
    ):
        st.session_state.structured = None
        st.session_state.structured_input_hash = None

    if "structured" not in st.session_state:
        st.session_state.structured = None

    st.header("7. Open-weight AI structuring")

    if st.button(
        "✨ Structure visit with Gemma",
        type="primary",
        use_container_width=True,
    ):
        if not time_valid:
            st.warning("Correct the observation date/time first.")
        elif (
            total_cats_seen == 0
            and not raw_notes.strip()
            and not biodiversity_notes.strip()
        ):
            st.warning("Record at least one observation before using the AI.")
        else:
            try:
                with st.spinner("Gemma is structuring the field record..."):
                    structured = structure_with_gemma(ai_input)

                st.session_state.structured = structured
                st.session_state.structured_input_hash = current_input_hash
                st.success("Structured. Review the AI output before saving.")
            except Exception as exc:
                st.error(str(exc))

    structured = st.session_state.get("structured")

    if structured:
        st.markdown("---")
        st.header("8. Review AI-structured record")

        st.warning(
            "Human review required. This tool does not diagnose, assess urgency, "
            "recommend treatment, or replace veterinary or colony-management judgement."
        )

        section_list("Observed facts", structured.get("observed_facts", []))

        st.markdown("#### Individuals")
        individuals = structured.get("individuals", [])
        if individuals:
            for individual in individuals:
                ident = individual.get("identifier", "Unidentified individual")
                with st.expander(ident):
                    observations = individual.get("observations", [])
                    if observations:
                        for obs in observations:
                            st.markdown(f"- {obs}")
                    else:
                        st.caption("No observations.")
        else:
            st.caption("No individual-level records.")

        section_list("Biodiversity", structured.get("biodiversity", []))
        section_list("Environment", structured.get("environment", []))
        section_list(
            "Uncertain / interpretive statements",
            structured.get("uncertain_or_interpretive_statements", []),
        )
        section_list("Follow-up flags", structured.get("follow_up_flags", []))

        visit = {
            "date": visit_date,
            "colony": colony.strip(),
            "observer": observer.strip(),
            "start_time": start_time_value.strftime("%H:%M"),
            "end_time": end_time_value.strftime("%H:%M"),
            "duration_minutes": duration_minutes,
            "cats_seen": int(total_cats_seen),
            "weather": weather,
            "raw_notes": raw_notes.strip(),
        }

        if st.button("💾 Save reviewed visit", use_container_width=True):
            if not time_valid:
                st.error(time_error)
            else:
                save_visit(
                    visit,
                    structured,
                    selected_cat_ids,
                    per_cat_notes,
                    unknown_cat_records,
                    food_water,
                    feeding_point,
                    biodiversity_notes,
                )
                st.session_state.flash_message = "Visit saved successfully."
                st.rerun()

        export_payload = {
            "project": "CatColonyWatch",
            "app_version": APP_VERSION,
            "visit": {**visit, "date": str(visit_date)},
            "known_cats_observed": [
                {
                    "name": get_cat(cat_id)["name"],
                    "notes": per_cat_notes.get(cat_id, ""),
                }
                for cat_id in selected_cat_ids
            ],
            "unknown_cats_observed": unknown_cat_records,
            "additional_cats_seen_not_recorded_individually": additional_unrecorded,
            "food_water": food_water,
            "feeding_point": feeding_point,
            "biodiversity_notes": biodiversity_notes,
            "ai_structured_record": structured,
            "model": get_model_id(),
            "human_review_required": True,
        }

        json_bytes = json.dumps(
            export_payload, ensure_ascii=False, indent=2
        ).encode("utf-8")

        csv_buffer = StringIO()
        pd.DataFrame(
            [
                {
                    "date": str(visit_date),
                    "start_time": visit["start_time"],
                    "end_time": visit["end_time"],
                    "duration_minutes": duration_minutes,
                    "colony": colony,
                    "observer": observer,
                    "cats_seen": total_cats_seen,
                    "known_cats_observed": " | ".join(
                        get_cat(cat_id)["name"] for cat_id in selected_cat_ids
                    ),
                    "unknown_cats_recorded": len(unknown_cat_records),
                    "additional_cats_not_recorded_individually": additional_unrecorded,
                    "weather": weather,
                    "food_water": food_water,
                    "feeding_point": feeding_point,
                    "raw_notes": raw_notes,
                    "observed_facts": " | ".join(
                        structured.get("observed_facts", [])
                    ),
                    "biodiversity": " | ".join(
                        structured.get("biodiversity", [])
                    ),
                    "environment": " | ".join(
                        structured.get("environment", [])
                    ),
                    "uncertain_or_interpretive_statements": " | ".join(
                        structured.get(
                            "uncertain_or_interpretive_statements", []
                        )
                    ),
                    "follow_up_flags": " | ".join(
                        structured.get("follow_up_flags", [])
                    ),
                }
            ]
        ).to_csv(csv_buffer, index=False)

        d1, d2 = st.columns(2)

        with d1:
            st.download_button(
                "⬇️ Download JSON",
                data=json_bytes,
                file_name="catcolonywatch_visit.json",
                mime="application/json",
                use_container_width=True,
            )

        with d2:
            st.download_button(
                "⬇️ Download CSV",
                data=csv_buffer.getvalue().encode("utf-8"),
                file_name="catcolonywatch_visit.csv",
                mime="text/csv",
                use_container_width=True,
            )


with tab_cats:
    st.header("🐈 Cat database")
    st.write(
        "Register a known cat once, then select that cat during future field visits."
    )

    mode = st.radio(
        "Action",
        ["Register new cat", "View / edit cats"],
        horizontal=True,
    )

    if mode == "Register new cat":
        with st.form(
            "new_cat_form",
            clear_on_submit=True,
            enter_to_submit=False,
        ):
            c1, c2 = st.columns(2)

            with c1:
                cat_name = st.text_input(
                    "Name or field name *",
                    placeholder="e.g. Mora",
                )
                cat_colony = st.text_input("Colony / feeding point")
                cat_sex = st.selectbox("Sex", SEX_OPTIONS)
                cat_age = st.selectbox("Estimated age", AGE_OPTIONS)
                cat_sterilised = st.selectbox("Sterilised", YES_NO_UNKNOWN)

            with c2:
                cat_ear_tip = st.selectbox(
                    "Ear tip / visible sterilisation mark",
                    YES_NO_UNKNOWN,
                )
                cat_identification = st.text_input(
                    "Optional existing identifier",
                    placeholder=(
                        "Microchip, tag or colony code, only if already known"
                    ),
                    help=(
                        "Optional. CatColonyWatch keeps its own internal "
                        "database key hidden from volunteers."
                    ),
                )
                cat_coat = st.text_input(
                    "Coat / identifying features",
                    placeholder=(
                        "e.g. black and white, small notch in right ear"
                    ),
                )
                cat_health = st.text_area(
                    "Health notes",
                    placeholder=(
                        "Known history or objective recurrent observations"
                    ),
                    height=100,
                )
                cat_notes = st.text_area(
                    "General notes",
                    placeholder=(
                        "Anything useful for future identification or monitoring"
                    ),
                    height=100,
                )

            st.markdown("#### Follow-up / decision")
            follow_up_text = st.text_area(
                "Next step or decision",
                placeholder=(
                    "e.g. Confirm sterilisation status; share observation with "
                    "the colony coordinator; continue monitoring."
                ),
                height=90,
            )

            f1, f2 = st.columns(2)

            with f1:
                follow_up_status = st.selectbox(
                    "Status", FOLLOW_UP_STATUS_OPTIONS
                )

            with f2:
                use_follow_up_date = st.checkbox("Add a target date")
                follow_up_date = None
                if use_follow_up_date:
                    follow_up_date = st.date_input(
                        "Target date",
                        value=date.today(),
                        min_value=date.today(),
                    )

            submitted = st.form_submit_button(
                "💾 Save cat",
                use_container_width=True,
            )

        if submitted:
            if not cat_name.strip():
                st.error("Name or field name is required.")
            else:
                add_cat(
                    {
                        "colony": cat_colony.strip(),
                        "name": cat_name.strip(),
                        "sex": cat_sex,
                        "estimated_age": cat_age,
                        "sterilised": cat_sterilised,
                        "ear_tip": cat_ear_tip,
                        "identification": cat_identification.strip(),
                        "coat_description": cat_coat.strip(),
                        "health_notes": cat_health.strip(),
                        "general_notes": cat_notes.strip(),
                        "follow_up_text": follow_up_text.strip(),
                        "follow_up_status": follow_up_status,
                        "follow_up_date": (
                            str(follow_up_date) if follow_up_date else ""
                        ),
                    }
                )
                st.session_state.flash_message = (
                    f"{cat_name.strip()} saved in the cat database."
                )
                st.session_state.scroll_to_top = True
                st.rerun()

    else:
        cats = get_cats(active_only=False)

        if not cats:
            st.info("No cats registered yet.")
        else:
            df = pd.DataFrame(cats)
            display_cols = [
                "name",
                "colony",
                "sex",
                "estimated_age",
                "sterilised",
                "ear_tip",
                "identification",
                "coat_description",
                "health_notes",
                "follow_up_text",
                "follow_up_status",
                "follow_up_date",
            ]

            st.dataframe(
                df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

            label_to_id = unique_cat_labels(cats)
            selected_label = st.selectbox(
                "Select a cat to edit",
                list(label_to_id.keys()),
            )
            cat = get_cat(label_to_id[selected_label])

            with st.form("edit_cat_form", enter_to_submit=False):
                e1, e2 = st.columns(2)

                with e1:
                    e_name = st.text_input(
                        "Name or field name",
                        value=cat["name"],
                    )
                    e_colony = st.text_input(
                        "Colony / feeding point",
                        value=cat["colony"] or "",
                    )
                    e_sex = st.selectbox(
                        "Sex",
                        SEX_OPTIONS,
                        index=SEX_OPTIONS.index(
                            cat["sex"] if cat["sex"] in SEX_OPTIONS else "Unknown"
                        ),
                    )
                    e_age = st.selectbox(
                        "Estimated age",
                        AGE_OPTIONS,
                        index=AGE_OPTIONS.index(
                            cat["estimated_age"]
                            if cat["estimated_age"] in AGE_OPTIONS
                            else "Unknown"
                        ),
                    )
                    e_sterilised = st.selectbox(
                        "Sterilised",
                        YES_NO_UNKNOWN,
                        index=YES_NO_UNKNOWN.index(
                            cat["sterilised"]
                            if cat["sterilised"] in YES_NO_UNKNOWN
                            else "Unknown"
                        ),
                    )

                with e2:
                    e_ear_tip = st.selectbox(
                        "Ear tip / visible sterilisation mark",
                        YES_NO_UNKNOWN,
                        index=YES_NO_UNKNOWN.index(
                            cat["ear_tip"]
                            if cat["ear_tip"] in YES_NO_UNKNOWN
                            else "Unknown"
                        ),
                    )
                    e_identification = st.text_input(
                        "Optional existing identifier",
                        value=cat["identification"] or "",
                    )
                    e_coat = st.text_input(
                        "Coat / identifying features",
                        value=cat["coat_description"] or "",
                    )
                    e_health = st.text_area(
                        "Health notes",
                        value=cat["health_notes"] or "",
                        height=100,
                    )
                    e_notes = st.text_area(
                        "General notes",
                        value=cat["general_notes"] or "",
                        height=100,
                    )

                st.markdown("#### Follow-up / decision")

                e_follow_up_text = st.text_area(
                    "Next step or decision",
                    value=cat.get("follow_up_text") or "",
                    height=90,
                )

                current_status = (
                    cat.get("follow_up_status") or "Pending / not decided"
                )
                if current_status not in FOLLOW_UP_STATUS_OPTIONS:
                    current_status = "Pending / not decided"

                e_follow_up_status = st.selectbox(
                    "Status",
                    FOLLOW_UP_STATUS_OPTIONS,
                    index=FOLLOW_UP_STATUS_OPTIONS.index(current_status),
                )

                existing_follow_up_date = cat.get("follow_up_date") or ""
                e_use_date = st.checkbox(
                    "Add / keep a target date",
                    value=bool(existing_follow_up_date),
                )

                e_follow_up_date = None
                if e_use_date:
                    try:
                        default_date = date.fromisoformat(existing_follow_up_date)
                    except Exception:
                        default_date = date.today()

                    e_follow_up_date = st.date_input(
                        "Target date",
                        value=max(default_date, date.today()),
                        min_value=date.today(),
                    )

                update_submitted = st.form_submit_button(
                    "💾 Save changes",
                    use_container_width=True,
                )

            if update_submitted:
                if not e_name.strip():
                    st.error("Name or field name is required.")
                else:
                    update_cat(
                        cat["id"],
                        {
                            "colony": e_colony.strip(),
                            "name": e_name.strip(),
                            "sex": e_sex,
                            "estimated_age": e_age,
                            "sterilised": e_sterilised,
                            "ear_tip": e_ear_tip,
                            "identification": e_identification.strip(),
                            "coat_description": e_coat.strip(),
                            "health_notes": e_health.strip(),
                            "general_notes": e_notes.strip(),
                            "follow_up_text": e_follow_up_text.strip(),
                            "follow_up_status": e_follow_up_status,
                            "follow_up_date": (
                                str(e_follow_up_date) if e_follow_up_date else ""
                            ),
                        },
                    )

                    st.session_state.flash_message = "Cat record updated."
                    st.rerun()


with tab_history:
    st.header("📚 Saved visits")
    visits = get_visits()

    if not visits:
        st.info("No visits saved yet.")
    else:
        st.dataframe(
            pd.DataFrame(visits),
            use_container_width=True,
            hide_index=True,
        )


st.markdown("---")
st.caption(
    "CatColonyWatch is an open-source prototype. "
    "AI structures observations; humans remain responsible "
    "for interpretation and action."
)
