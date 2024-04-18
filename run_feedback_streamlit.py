import streamlit as st
from feedback_generation import generate_feedback, gec, rank_errors
import random
import json

@st.cache_resource
def input_and_feedback(user_text, level, l1):
    # Get suggested edits from gec function
    edits, cor_lines = gec(user_text)
    errors_to_present = rank_errors(edits)

    feedback = json.loads(generate_feedback(errors_to_present, level, l1))
    
    return feedback, errors_to_present

def main():
    st.title("Grammatical Error Feedback App")
    
    l1 = st.selectbox("Select your native language", ["English", "Spanish", "Mandarin Chinese", "Other"])
    level = st.selectbox("Select your course level", ["Beginner", "Intermediate", "Advanced"])
    user_text = st.text_area("Write your essay in Spanish")

    feedback, errors_to_present = input_and_feedback(user_text, level, l1)

    # Initialize step counter
    step = 0
    
    if not feedback:
        st.warning("I didn't find any errors to correct. Good job! Of course, this doesn't mean your essay is perfect. I just didn't find anything I have suggestions on how to fix.")
        return

    # Display feedback step by step
    for item, edit, i in zip(feedback, errors_to_present, range(len(errors_to_present))):
        edit_obj = edit[2]
        target_tok = edit_obj.c_str
            
        with st.form(f'my_form_{i}'):
                
            if feedback[item]['line_1']:
                feedback_1 = feedback[item]['line_1']

                print(feedback_1)

                student_resp = st.text_input(f"Feedback {i + 1}: {feedback_1}\nYour correction:", key=f'feedback_step_{i}')

                submit_click = st.form_submit_button('Submit')

                if submit_click:
                    if target_tok.lower() in student_resp.lower():
                        st.success(feedback[item]['response_1']['correct'])
                    else:
                        st.warning(feedback[item]['response_1']['incorrect'])
                        student_resp2 = st.text_input('Your correction:', key=f'response_step_{i}')

                        if target_tok.lower() in student_resp2.lower():
                            st.success(feedback[item]['response_2']['correct'])
                        else:
                            st.warning(feedback[item]['response_2']['incorrect'])
                            
            else:
                st.warning(feedback[item]['llm_explanation'])
                student_resp = st.text_input(f"Please rewrite the sentence based on this feedback: ", key=f'response_step_{i}')
                submit_click3 = st.form_submit_button('Submit')
                if submit_click3:
                    st.success("Good job")


            # Wait for student input before proceeding to the next step
        if st.button("Next Item", key=f'next_item_{i}'):
            step += 1  # Increment step counter
            #st.empty()  # Clear previous messages


if __name__ == "__main__":
    main()