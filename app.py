import streamlit as st
import time
import pandas as pd
from datetime import datetime
import cv2
import streamlit.components.v1 as components

from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
from streamlit_autorefresh import st_autorefresh

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AI Physiotherapy Trainer", layout="wide")

st.markdown(
    """
    <h1 style="text-align:center; color:#1e3c72;">
    🏋️ AI-Based Physiotherapy Exercise Trainer
    </h1>
    """,
    unsafe_allow_html=True
)

# ---------------- BEEP SOUND FUNCTION ----------------
def beep():
    components.html(
        """
        <script>
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = 900;
        gain.gain.value = 0.15;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        setTimeout(() => { osc.stop(); ctx.close(); }, 200);
        </script>
        """,
        height=0,
    )

# ---------------- CONSTANTS ----------------
START_DELAY = 10
TARGET_REPS = 5
REP_HOLD_SECONDS = 15

# ---------------- SESSION STATE ----------------
defaults = {
    "camera_on": False,
    "paused": False,
    "start_time": None,
    "pause_start": None,
    "total_pause_time": 0.0,
    "rep_count": 0,
    "rep_start_time": None,
    "rep_elapsed_frozen": 0,
    "frozen_elapsed": 0,
    "session_report": [],
    "beep_start_done": False,
    "last_beep_rep": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- DIET PLAN ----------------
DIET_PLAN = {
    "Before Exercise": [
        "Drink water (1 glass).",
        "Eat a light snack if needed (banana/fruit)."
    ],
    "After Exercise": [
        "Drink water again.",
        "Eat protein-rich food (eggs, milk, dal)."
    ],
    "Best Foods for Recovery": [
        "Fruits & vegetables",
        "Nuts & seeds",
        "Curd / milk",
        "Whole grains"
    ],
    "Avoid": [
        "Too much oily food",
        "Cold drinks after exercise",
        "Skipping meals"
    ]
}

# ---------------- FULL UPDATED EXERCISE LIST ----------------
EXERCISES = {
    "Spine (Neck & Back)": {
        "Stretching / Mobility": [
            {"name": "Chin Tucks", "duration": "10 reps (hold 3 sec)",
             "steps": ["Sit/stand straight.", "Pull chin backward (double chin).", "Hold and relax slowly."],
             "tip": "Do not bend your head down."},
            {"name": "Cat-Cow Stretch", "duration": "8–10 reps",
             "steps": ["Come to hands and knees.", "Arch back upward (Cat).", "Drop belly down and lift chest (Cow)."],
             "tip": "Move slowly with breathing."},
            {"name": "Knee-to-Chest", "duration": "10 reps each leg",
             "steps": ["Lie on your back.", "Bring one knee to your chest.", "Hold and switch legs."],
             "tip": "Keep lower back relaxed."},
            {"name": "Lower Back Rotations", "duration": "10 reps each side",
             "steps": ["Lie on back, knees bent.", "Drop knees side-to-side slowly."],
             "tip": "Keep shoulders flat on floor."},
            {"name": "Child’s Pose", "duration": "Hold 20–30 sec",
             "steps": ["Sit on heels.", "Stretch arms forward.", "Relax and breathe."],
             "tip": "Do not force stretch."},
            {"name": "Thoracic Extensions", "duration": "8 reps",
             "steps": ["Sit on chair, hands behind head.", "Arch upper back gently.", "Return slowly."],
             "tip": "Do not strain your neck."}
        ],
        "Strengthening / Stability": [
            {"name": "Pelvic Tilts", "duration": "10 reps",
             "steps": ["Lie on back, knees bent.", "Flatten lower back into floor.", "Relax and repeat."],
             "tip": "Do not hold your breath."},
            {"name": "Bird-Dog", "duration": "8 reps each side",
             "steps": ["Hands and knees position.", "Extend opposite arm and leg.", "Hold and return slowly."],
             "tip": "Keep spine straight."},
            {"name": "Dead Bug", "duration": "8 reps each side",
             "steps": ["Lie on your back, knees up.", "Lower opposite arm and leg slowly.", "Return and repeat."],
             "tip": "Keep lower back flat."},
            {"name": "Glute Bridges", "duration": "10 reps (hold 3 sec)",
             "steps": ["Lie on your back, knees bent.", "Lift hips upward.", "Hold and lower slowly."],
             "tip": "Do not over-arch the back."},
            {"name": "Plank (Wall/Floor)", "duration": "Hold 15–30 sec",
             "steps": ["Keep body straight.", "Tighten core.", "Hold position."],
             "tip": "Avoid hips dropping."},
            {"name": "Superman", "duration": "8 reps (hold 2 sec)",
             "steps": ["Lie face down.", "Lift chest and legs slightly.", "Hold and relax."],
             "tip": "Do not strain neck."}
        ]
    },

    "Shoulder & Upper Body": {
        "Stretching / Mobility": [
            {"name": "Pendulum Swings", "duration": "30 sec",
             "steps": ["Lean forward, arm relaxed.", "Swing small circles slowly."],
             "tip": "Do not force motion."},
            {"name": "Doorway Chest Stretch", "duration": "Hold 20 sec",
             "steps": ["Arms on doorway.", "Step forward gently."],
             "tip": "Keep shoulders down."},
            {"name": "Cross-Body Shoulder Stretch", "duration": "Hold 20 sec each",
             "steps": ["Pull arm across chest.", "Hold and switch."],
             "tip": "No jerky pull."},
            {"name": "Wall Slides", "duration": "10 reps",
             "steps": ["Back to wall.", "Slide arms up slowly."],
             "tip": "Move slowly and controlled."}
        ],
        "Strengthening": [
            {"name": "Scapular Squeezes", "duration": "12 reps",
             "steps": ["Pinch shoulder blades together.", "Relax slowly."],
             "tip": "Do not shrug shoulders."},
            {"name": "External/Internal Rotations", "duration": "10 reps each",
             "steps": ["Rotate arm slowly (band optional)."],
             "tip": "Keep elbow close to body."},
            {"name": "I-Y-T Raises", "duration": "8 reps each",
             "steps": ["Lift arms in I, Y, T shape slowly."],
             "tip": "Small controlled movement."},
            {"name": "Wall Push-ups", "duration": "10 reps",
             "steps": ["Hands on wall.", "Push slowly."],
             "tip": "Keep body straight."}
        ]
    },

    "Hip, Knee, & Leg": {
        "Stretching / Mobility": [
            {"name": "Hamstring Stretch", "duration": "Hold 20 sec",
             "steps": ["Stretch hamstring gently."], "tip": "No bouncing."},
            {"name": "Quadriceps Stretch", "duration": "Hold 20 sec each",
             "steps": ["Pull heel to glutes gently."], "tip": "Keep knees close."},
            {"name": "Hip Flexor Lunge", "duration": "Hold 20 sec each",
             "steps": ["Push hips forward slowly."], "tip": "Back straight."},
            {"name": "Pigeon Stretch", "duration": "Hold 20 sec",
             "steps": ["Stretch hip gently."], "tip": "Only if comfortable."},
            {"name": "Heel Slides", "duration": "10 reps",
             "steps": ["Slide heel toward buttock slowly."], "tip": "Controlled movement."}
        ],
        "Strengthening": [
            {"name": "Straight Leg Raises (SLR)", "duration": "10 reps each",
             "steps": ["Raise straight leg slowly."], "tip": "Keep knee straight."},
            {"name": "Clamshells", "duration": "12 reps each",
             "steps": ["Lift top knee, feet together."], "tip": "Do not roll hips."},
            {"name": "Quad Sets", "duration": "10 reps (hold 5 sec)",
             "steps": ["Press knee down into floor."], "tip": "Feel thigh tighten."},
            {"name": "Mini Squats / Wall Sits", "duration": "8 reps",
             "steps": ["Small squats or wall sit hold."], "tip": "Knees not past toes."},
            {"name": "Step-Ups", "duration": "10 reps each",
             "steps": ["Step up and down slowly."], "tip": "Hold support if needed."},
            {"name": "Lateral Leg Raises", "duration": "10 reps each",
             "steps": ["Lift leg sideways slowly."], "tip": "Do not lean body."}
        ]
    },

    "Ankle, Foot, & Wrist": {
        "Ankle & Foot": [
            {"name": "Ankle Pumps", "duration": "15 reps",
             "steps": ["Move foot up/down slowly."], "tip": "Full range motion."},
            {"name": "Ankle Alphabet", "duration": "A–Z once",
             "steps": ["Draw letters using toes."], "tip": "Slow movement."},
            {"name": "Calf Raises", "duration": "12 reps",
             "steps": ["Rise on toes and lower slowly."], "tip": "Use chair support."},
            {"name": "Towel Curls", "duration": "10 reps",
             "steps": ["Scrunch towel with toes."], "tip": "Do slowly."}
        ],
        "Wrist & Hand": [
            {"name": "Wrist Flexor/Extensor Stretch", "duration": "Hold 15 sec each",
             "steps": ["Pull hand back gently.", "Push hand down gently."],
             "tip": "No pain."},
            {"name": "Wrist Circles", "duration": "10 circles each",
             "steps": ["Rotate wrists slowly."], "tip": "Smooth motion."},
            {"name": "Finger Isometric Squeezes", "duration": "10 squeezes",
             "steps": ["Squeeze soft ball/putty."], "tip": "Do not over squeeze."}
        ]
    },

    "Balance & Coordination": {
        "Exercises": [
            {"name": "Single-Leg Balance", "duration": "Hold 20 sec each",
             "steps": ["Stand on one foot near support."], "tip": "Safety first."},
            {"name": "Heel-to-Toe Walk", "duration": "10 steps",
             "steps": ["Walk in a straight line slowly."], "tip": "Go slow."},
            {"name": "Sit-to-Stand", "duration": "8 reps",
             "steps": ["Stand up from chair without hands."], "tip": "Use hands only if needed."},
            {"name": "Side-Stepping", "duration": "10 steps each side",
             "steps": ["Walk sideways slowly."], "tip": "Keep knees slightly bent."}
        ]
    }
}

# ✅ Auto refresh only while session is ON (makes countdown + timers smooth)
if st.session_state.camera_on:
    st_autorefresh(interval=500, key="physio_refresh")

# ---------------- UI: USER DETAILS ----------------
st.markdown("## 👤 User Details")
colA, colB, colC, colD = st.columns(4)

with colA:
    name = st.text_input("Name")
with colB:
    age = st.number_input("Age", min_value=1, max_value=100, value=18)
with colC:
    weight = st.number_input("Weight (kg)", min_value=10.0, max_value=200.0, value=50.0)
with colD:
    gender = st.selectbox("Gender", ["Female", "Male", "Other"])

# ---------------- MAIN LAYOUT ----------------
left, right = st.columns([2, 1])

with left:
    st.markdown("## ✅ Select Exercise")
    category = st.selectbox("Category", list(EXERCISES.keys()))
    ex_type = st.selectbox("Type", list(EXERCISES[category].keys()))
    exercise_names = [e["name"] for e in EXERCISES[category][ex_type]]
    selected_ex_name = st.selectbox("Exercise", exercise_names)
    selected_ex = next(e for e in EXERCISES[category][ex_type] if e["name"] == selected_ex_name)

with right:
    st.markdown("## 🥗 Diet Plan")
    for k, items in DIET_PLAN.items():
        st.markdown(f"**{k}:**")
        for it in items:
            st.write(f"✅ {it}")

# ---------------- BUTTONS ----------------
b1, b2, b3 = st.columns(3)

def save_report(status="Stopped"):
    if st.session_state.start_time is None:
        total_time = 0
    else:
        total_time = int((time.time() - st.session_state.start_time) - st.session_state.total_pause_time)
        if total_time < 0:
            total_time = 0

    st.session_state.session_report.append({
        "DateTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Name": name,
        "Age": age,
        "Weight(kg)": weight,
        "Gender": gender,
        "Category": category,
        "Type": ex_type,
        "Exercise": selected_ex["name"],
        "Target Reps": TARGET_REPS,
        "Completed Reps": st.session_state.rep_count,
        "Hold Time(s)": REP_HOLD_SECONDS,
        "Total Session Time(s)": total_time,
        "Status": status
    })

with b1:
    if st.button("▶ Start Camera", use_container_width=True):
        st.session_state.camera_on = True
        st.session_state.paused = False
        st.session_state.start_time = time.time()
        st.session_state.total_pause_time = 0.0
        st.session_state.pause_start = None
        st.session_state.rep_count = 0
        st.session_state.rep_start_time = None
        st.session_state.rep_elapsed_frozen = 0
        st.session_state.frozen_elapsed = 0
        st.session_state.beep_start_done = False
        st.session_state.last_beep_rep = 0

with b2:
    if st.button("⏸ Pause / Resume", use_container_width=True):
        if st.session_state.camera_on:
            if not st.session_state.paused:
                # ✅ Pausing now
                st.session_state.paused = True

                # Freeze total elapsed
                st.session_state.frozen_elapsed = int(
                    time.time() - st.session_state.start_time - st.session_state.total_pause_time
                )

                # Freeze rep elapsed
                if st.session_state.rep_start_time is not None:
                    st.session_state.rep_elapsed_frozen = int(time.time() - st.session_state.rep_start_time)
                else:
                    st.session_state.rep_elapsed_frozen = 0

                st.session_state.pause_start = time.time()

            else:
                # ✅ Resuming now
                st.session_state.paused = False

                if st.session_state.pause_start is not None:
                    st.session_state.total_pause_time += (time.time() - st.session_state.pause_start)
                    st.session_state.pause_start = None

                # Adjust rep_start_time so rep timer resumes correctly
                if st.session_state.rep_start_time is not None:
                    st.session_state.rep_start_time = time.time() - st.session_state.rep_elapsed_frozen

with b3:
    if st.button("⛔ Stop", use_container_width=True):
        save_report(status="Stopped by User")
        st.session_state.camera_on = False
        st.session_state.paused = False

st.divider()

# ---------------- CAMERA + INSTRUCTIONS ABOVE REPORT ----------------
video_col, side_col = st.columns([3, 1])

class VideoProcessor(VideoProcessorBase):
    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")

        # ✅ FIX MIRROR (force correct view)
        img = cv2.flip(img, 1)

        # ✅ No heavy drawing for speed
        return frame.from_ndarray(img, format="bgr24")

with video_col:
    st.markdown("## 🎥 Camera")

    webrtc_ctx = webrtc_streamer(
        key="physio-cam",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=VideoProcessor,
        media_stream_constraints={
            "video": {"width": 640, "height": 480, "frameRate": 15},
            "audio": False
        },
        async_processing=False,
    )

with side_col:
    st.markdown("## 🧠 Instructions")
    guidance_box = st.empty()

    st.markdown("## 📊 Live Feedback")
    feedback_box = st.empty()

    st.markdown("## ✅ Progress")
    progress_bar = st.progress(0)

steps_text = ""
for i, s in enumerate(selected_ex["steps"], start=1):
    steps_text += f"{i}. {s}\n"

guidance_box.markdown(
    f"### ✅ {selected_ex['name']}\n\n"
    f"**Duration/Target:** {selected_ex['duration']}\n\n"
    f"**Steps:**\n{steps_text}\n"
    f"✅ **Tip:** {selected_ex['tip']}"
)

# ---------------- TIMER + REPS LOGIC ----------------
instruction = "Select exercise and click Start ✅"

if not st.session_state.camera_on:
    feedback_box.info("Select exercise and click **Start Camera** ✅")
    progress_bar.progress(0)

else:
    if st.session_state.paused:
        effective_elapsed = st.session_state.frozen_elapsed
    else:
        effective_elapsed = int(time.time() - st.session_state.start_time - st.session_state.total_pause_time)

    remaining_start = max(0, START_DELAY - effective_elapsed)

    if remaining_start > 0:
        instruction = f"STARTING IN {remaining_start}"
        feedback_box.markdown("⏳ Get Ready...")
        progress_bar.progress(st.session_state.rep_count / TARGET_REPS)

    else:
        if not st.session_state.beep_start_done:
            beep()
            st.session_state.beep_start_done = True

        if st.session_state.rep_start_time is None:
            st.session_state.rep_start_time = time.time()

        if st.session_state.paused:
            rep_elapsed = st.session_state.rep_elapsed_frozen
        else:
            rep_elapsed = int(time.time() - st.session_state.rep_start_time)

        remaining_rep = max(0, REP_HOLD_SECONDS - rep_elapsed)

        if st.session_state.paused:
            instruction = "⏸ PAUSED"
            feedback_box.markdown("⏸ Session paused.")
        else:
            instruction = f"HOLD {remaining_rep}s"

            if rep_elapsed >= REP_HOLD_SECONDS:
                st.session_state.rep_count += 1
                st.session_state.rep_start_time = time.time()

                if st.session_state.rep_count != st.session_state.last_beep_rep:
                    beep()
                    st.session_state.last_beep_rep = st.session_state.rep_count

        feedback_box.markdown(
            f"✅ Reps: **{st.session_state.rep_count}/{TARGET_REPS}**\n\n"
            f"🕒 Session Time: **{effective_elapsed}s**"
        )
        progress_bar.progress(min(1.0, st.session_state.rep_count / TARGET_REPS))

        if st.session_state.rep_count >= TARGET_REPS:
            beep()
            beep()
            save_report(status="Completed")
            st.success("🎉 Exercise Completed Successfully!")
            st.session_state.camera_on = False

    st.markdown(
        f"""
        <div style="padding:15px; background:#1e3c72; border-radius:12px; color:white; font-size:24px; font-weight:bold;">
        ✅ LIVE INSTRUCTION: {instruction}
        </div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# ---------------- REPORT SECTION BELOW CAMERA ----------------
st.markdown("## 📄 Exercise Session Report")

if len(st.session_state.session_report) == 0:
    st.info("No session report yet. Complete an exercise or stop the session to generate report ✅")
else:
    df_report = pd.DataFrame(st.session_state.session_report)
    st.dataframe(df_report, use_container_width=True)

    csv_data = df_report.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download Report (CSV)",
        data=csv_data,
        file_name="physio_session_report.csv",
        mime="text/csv"
    )
