import streamlit as st
import json
import os
import random
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt


# -----------------------
# Constants & File paths
# -----------------------
QUESTIONS_FILE = "questions.json"
RESULTS_FILE = "results.json"

# -----------------------
# Helper functions
# -----------------------
def ensure_files_exist():
    """Create default question file and results file if missing."""
    if not os.path.exists(QUESTIONS_FILE):
        default_questions = [
            {
                "id": 1,
                "category": "General Knowledge",
                "question": "What is the capital of France?",
                "choices": ["Paris", "London", "Berlin", "Madrid"],
                "answer": "Paris"
            },
            {
                "id": 2,
                "category": "Math",
                "question": "What is 7 * 8?",
                "choices": ["54", "56", "58", "49"],
                "answer": "56"
            },
            {
                "id": 3,
                "category": "Science",
                "question": "Water's chemical formula is?",
                "choices": ["H2O", "CO2", "O2", "NaCl"],
                "answer": "H2O"
            }
        ]
        with open(QUESTIONS_FILE, "w") as f:
            json.dump(default_questions, f, indent=2)

    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w") as f:
            json.dump([], f, indent=2)

def load_questions():
    """Return list of question dicts."""
    with open(QUESTIONS_FILE, "r") as f:
        return json.load(f)

def save_questions(qs):
    """Persist list of questions to file."""
    with open(QUESTIONS_FILE, "w") as f:
        json.dump(qs, f, indent=2)
    st.success("Question bank saved.")

def load_results():
    with open(RESULTS_FILE, "r") as f:
        return json.load(f)

def save_result(result):
    results = load_results()
    results.append(result)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    st.success("Result saved.")

def generate_id(qs):
    if not qs:
        return 1
    return max(q["id"] for q in qs) + 1

def get_categories(qs):
    cats = sorted(list({q["category"] for q in qs}))
    return cats

def quiz_session_reset():
    st.session_state["current_q_index"] = 0
    st.session_state["score"] = 0
    st.session_state["answers"] = []

def calculate_grade(score, total):
    pct = (score / total) * 100 if total > 0 else 0
    if pct >= 85:
        grade = "A"
    elif pct >= 70:
        grade = "B"
    elif pct >= 50:
        grade = "C"
    else:
        grade = "D"
    return pct, grade

# -----------------------
# Layout parts
# -----------------------
def flash_screen():
    st.title(" Smart Quiz & Progress Tracker")
    st.write("""
    Welcome! This app demonstrates a Streamlit GUI for a quiz system with persistent storage, 
    question management (add/edit/delete), results tracking, and visual progress feedback.
    """)
    st.markdown("---")
    st.info("Use the sidebar to navigate: Flash Screen, Take Quiz, View Results, Edit Questions, Display Questions")

def take_quiz():
    st.header("📝 Take Quiz")
    qs = load_questions()
    if not qs:
        st.warning("No questions available. Please add questions in 'Edit Questions'.")
        return

    categories = ["All"] + get_categories(qs)
    category = st.selectbox("Choose category", categories)

    num_questions = st.slider("Number of questions", min_value=1, max_value=min(20, len(qs)), value=min(5, len(qs)))
    shuffle = st.checkbox("Shuffle questions", value=True)

    # Filter questions
    if category == "All":
        pool = qs.copy()
    else:
        pool = [q for q in qs if q["category"] == category]

    if not pool:
        st.warning("No questions in this category.")
        return

    if shuffle:
        random.shuffle(pool)

    selected_questions = pool[:num_questions]

    # initialize session state
    if "quiz_running" not in st.session_state or st.session_state.get("last_pool") != [q["id"] for q in selected_questions]:
        st.session_state["quiz_running"] = True
        st.session_state["last_pool"] = [q["id"] for q in selected_questions]
        quiz_session_reset()
        st.session_state["start_time"] = datetime.now().isoformat()

    q_index = st.session_state.get("current_q_index", 0)

    # Display current question
    q = selected_questions[q_index]
    st.subheader(f"Question {q_index + 1} of {len(selected_questions)}")
    st.write(f"*{q['question']}*")
    choice = st.radio("Choose an answer", q["choices"], key=f"choice_{q['id']}")

    cols = st.columns([1,1,1])
    with cols[0]:
        if st.button("Previous") and q_index > 0:
            st.session_state["current_q_index"] -= 1
    with cols[1]:
        if st.button("Submit Answer"):
            st.session_state["answers"] = st.session_state.get("answers", [])
            # store tuple (q_id, selected_choice, correct)
            correct = choice == q["answer"]
            # update score only if this question hasn't been answered yet
            already = next((a for a in st.session_state["answers"] if a[0] == q["id"]), None)
            if already is None:
                st.session_state["answers"].append((q["id"], choice, correct))
                if correct:
                    st.session_state["score"] = st.session_state.get("score", 0) + 1
                    st.success("Correct!")
                else:
                    st.error(f"Incorrect. Correct answer: *{q['answer']}*")
            else:
                st.info("You already answered this question. Use Next/Previous to move.")
    with cols[2]:
        if st.button("Next") and q_index < len(selected_questions) - 1:
            st.session_state["current_q_index"] += 1

    # If last question and user finished
    if q_index == len(selected_questions) - 1:
        st.markdown("---")
        if st.button("Finish Quiz"):
            total = len(selected_questions)
            score = st.session_state.get("score", 0)
            pct, grade = calculate_grade(score, total)
            st.success(f"You scored {score}/{total} — {pct:.1f}%  (Grade: {grade})")
            # Save result
            result = {
                "timestamp": datetime.now().isoformat(),
                "score": score,
                "total": total,
                "pct": pct,
                "grade": grade,
                "category": category,
                "answers": st.session_state.get("answers", [])
            }
            save_result(result)
            st.session_state["quiz_running"] = False

            # Show progress chart
            st.write("### Progress chart (Last results)")
            results = load_results()
            df = pd.DataFrame(results)
            if not df.empty:
                # show last 10 attempts
                df_recent = df.tail(10)
                fig, ax = plt.subplots()
                ax.plot(range(len(df_recent)), df_recent["pct"].astype(float), marker="o")
                ax.set_xticks(range(len(df_recent)))
                ax.set_xticklabels([d.split("T")[0] for d in df_recent["timestamp"]], rotation=45)
                ax.set_ylabel("Percentage")
                ax.set_ylim(0, 100)
                ax.set_title("Last attempts (%)")
                st.pyplot(fig)
            else:
                st.info("No results to display yet.")

def display_questions():
    st.header("📚 Display Questions")
    qs = load_questions()
    if not qs:
        st.warning("No questions available.")
        return

    df = pd.DataFrame(qs)
    st.dataframe(df[["id","category","question","choices","answer"]])

    # Optional: filter and view
    category = st.selectbox("Filter by category", ["All"] + get_categories(qs))
    if st.button("Apply Filter"):
        if category == "All":
            filtered = qs
        else:
            filtered = [q for q in qs if q["category"] == category]
        st.write(f"Showing {len(filtered)} question(s).")
        for q in filtered:
            st.markdown(f"*{q['id']}. [{q['category']}] {q['question']}*")
            st.write("Choices: " + ", ".join(q["choices"]))
            st.write(f"Answer: *{q['answer']}*")
            st.markdown("---")

def view_results():
    st.header("📈 View Results")
    results = load_results()
    if not results:
        st.info("No results yet. Take a quiz to generate results.")
        return
    df = pd.DataFrame(results)
    st.dataframe(df[["timestamp","score","total","pct","grade","category"]])

    # Summary stats
    st.write("### Summary")
    avg_pct = df["pct"].astype(float).mean()
    best = df.loc[df["pct"].astype(float).idxmax()]
    st.write(f"- Attempts: {len(df)}")
    st.write(f"- Average %: {avg_pct:.2f}")
    st.write(f"- Best: {best['pct']}% on {best['timestamp'].split('T')[0]} (Grade: {best['grade']})")

    # Plot distribution
    fig, ax = plt.subplots()
    ax.hist(df["pct"].astype(float), bins=8)
    ax.set_xlabel("Percentage")
    ax.set_ylabel("Count")
    ax.set_title("Distribution of Scores (%)")
    st.pyplot(fig)

    # Download results
    csv = df.to_csv(index=False)
    st.download_button("Download results CSV", data=csv, file_name="quiz_results.csv", mime="text/csv")

def edit_questions():
    st.header("✏️ Edit Questions (Add / Edit / Delete)")
    qs = load_questions()
    mode = st.radio("Mode", ["Add Question", "Edit Existing", "Delete Question", "Bulk Reset to Default"])

    if mode == "Add Question":
        with st.form("add_q_form"):
            category = st.text_input("Category", value="General")
            question = st.text_area("Question")
            choices_raw = st.text_area("Choices (one per line)")
            answer = st.text_input("Correct answer (must exactly match one of choices)")
            submitted = st.form_submit_button("Add Question")
            if submitted:
                choices = [c.strip() for c in choices_raw.splitlines() if c.strip()]
                if not question or not choices or answer.strip() == "":
                    st.error("Please provide question, choices and answer.")
                elif answer not in choices:
                    st.error("Answer must match one of the choices exactly.")
                else:
                    new_id = generate_id(qs)
                    new_q = {"id": new_id, "category": category, "question": question, "choices": choices, "answer": answer}
                    qs.append(new_q)
                    save_questions(qs)
                    st.success(f"Question added with id {new_id}.")

    elif mode == "Edit Existing":
        if not qs:
            st.warning("No questions to edit.")
            return
        options = {f"{q['id']}: {q['question'][:50]}": q["id"] for q in qs}
        sel = st.selectbox("Select question to edit", list(options.keys()))
        qid = options[sel]
        q = next(q for q in qs if q["id"] == qid)
        with st.form("edit_q_form"):
            category = st.text_input("Category", value=q["category"])
            question = st.text_area("Question", value=q["question"])
            choices_raw = st.text_area("Choices (one per line)", value="\n".join(q["choices"]))
            answer = st.text_input("Correct answer", value=q["answer"])
            submitted = st.form_submit_button("Save Changes")
            if submitted:
                choices = [c.strip() for c in choices_raw.splitlines() if c.strip()]
                if answer not in choices:
                    st.error("Answer must match one of the choices.")
                else:
                    q["category"] = category
                    q["question"] = question
                    q["choices"] = choices
                    q["answer"] = answer
                    save_questions(qs)
                    st.success("Question updated.")

    elif mode == "Delete Question":
        if not qs:
            st.warning("No questions to delete.")
            return
        options = {f"{q['id']}: {q['question'][:50]}": q["id"] for q in qs}
        sel = st.selectbox("Select question to delete", list(options.keys()))
        qid = options[sel]
        if st.button("Delete"):
            new_qs = [q for q in qs if q["id"] != qid]
            save_questions(new_qs)
            st.success(f"Question {qid} deleted.")

    elif mode == "Bulk Reset to Default":
        st.warning("This will overwrite your current question bank with the default sample questions.")
        if st.button("Reset to Default"):
            if os.path.exists(QUESTIONS_FILE):
                os.remove(QUESTIONS_FILE)
            ensure_files_exist()
            st.success("Question bank reset to default.")

# -----------------------
# Main
# -----------------------
def main():
    st.set_page_config(page_title="Smart Quiz & Progress Tracker", layout="wide")
    ensure_files_exist()

    # Sidebar navigation
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Go to", ["Flash Screen", "Take Quiz", "View Results", "Edit Questions", "Display Questions", "About"])

    # Flashy quick actions
    if st.sidebar.button("Reset Quiz Session"):
        quiz_session_reset()
        st.success("Quiz session reset.")

    # Show selected page
    if choice == "Flash Screen":
        flash_screen()
    elif choice == "Take Quiz":
        take_quiz()
    elif choice == "View Results":
        view_results()
    elif choice == "Edit Questions":
        edit_questions()
    elif choice == "Display Questions":
        display_questions()
    elif choice == "About":
        st.header("About")
        st.markdown("""
        *Smart Quiz & Progress Tracker*
        - Demonstrates GUI navigation and Streamlit widgets.
        - Saves questions and results locally as JSON files.
        - Shows examples of programming concepts: variables, selections, loops, functions, lists/dicts, file I/O.
        - Authors: Your group (replace this text with your names in the final submission).
        """)
        st.markdown("### Instructions")
        st.markdown("""
        1. Use *Edit Questions* to add/edit/delete questions.  
        2. Go to *Take Quiz* to start a quiz.  
        3. After finishing, view aggregated results in *View Results*.  
        4. Use *Display Questions* to view the question bank table.
        """)

if _name_ == "_main_":
    main()