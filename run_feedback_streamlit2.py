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
    user_text = st.text_area("Write your essay in Spanish", height=300)
    
    st.write(f'You wrote {len(user_text.split(' '))} words.')
    
    if 'previous_submission' in st.session_state:
        resubmit = st.button('Re-submit essay')
        submit = True
        feedback, errors_to_present = input_and_feedback(user_text, level, l1)
        num_errors = len(errors_to_present)
        if resubmit:
            for i in range(1, num_errors + 1):
                if f'error_form_{i}' in st.session_state:
                    st.session_state[f'error_form_{i}'] = False
                    
            
    else:
        submit = st.button('Submit essay')
        st.session_state['previous_submission'] = True
        feedback, errors_to_present = input_and_feedback(user_text, level, l1)
    
    num_errors = len(errors_to_present)

    # Initialize step counter
    step = 0
    
    if submit:
        if num_errors == 0:
            st.warning("I didn't find any errors to correct. Good job! Of course, this doesn't mean your essay is perfect. I just didn't find anything I have suggestions on how to fix.")
            return

    for i in range(num_errors + 1):
        if f'error_form_{i}' not in st.session_state:
            st.session_state[f'error_form_{i}'] = False
            st.session_state.pop(f'student_resp_{i}', None)
            #Keep adding keys to remove here
    
    st.session_state.error_form_0 = True
        
    
    # Display feedback step by step
    for item, edit, i in zip(feedback, errors_to_present, range(1, num_errors + 1)):
        
        edit_obj = edit[2]
        target_tok = edit_obj.c_str
            
        if st.session_state[f'error_form_{i - 1}']:

            with st.form(f'my_form_{i}'):

                if feedback[item]['line_1']:
                    feedback_1 = feedback[item]['line_1']
                    
                    if f'student_resp_{i}' in st.session_state:
                        student_resp = st.session_state[f'student_resp_{i}']
                        st.write(f"Feedback {i}: {feedback_1}")
                        st.text_input(f"Your correction:", key=f'resp_{i}', value=student_resp)

                    else:
                        st.write(f"Feedback {i}: {feedback_1}")
                        student_resp = st.text_input(f"Your correction:", key=f'resp_{i}')
                        
                    print(target_tok.lower())
                    print(student_resp.lower())

                    if f'my_form_{i}_submit_click' in st.session_state:
                        submit_click = st.session_state[f'my_form_{i}_submit_click']
                        
                    else:
                        submit_click = st.form_submit_button('Submit A')

                    if submit_click:
                        
                        st.session_state[f'student_resp_{i}'] = student_resp
                        
                        if f'my_form_{i}_submit_click' not in st.session_state:
                            st.session_state[f'my_form_{i}_submit_click'] = True
                        
                        if target_tok.lower() in student_resp.lower():
                            st.success(feedback[item]['response_1']['correct'])
                            st.session_state[f'error_form_{i}'] = True
                            st.form_submit_button('Next feedback item')
                            
                        else:
                            st.warning(feedback[item]['response_1']['incorrect'])
                            
                            if f'student_resp2_{i}' in st.session_state:
                                student_resp2 = st.session_state[f'student_resp2_{i}']
                                st.text_input('Your correction:', key=f'resp2_{i}', value=student_resp2)
                            
                            else:
                                student_resp2 = st.text_input('Your correction:', key=f'resp2_{i}')
                            
                            if f'my_form_{i}_submit_click2' in st.session_state:
                                submit_click2 = st.session_state[f'my_form_{i}_submit_click2']
                        
                            else:
                                submit_click2 = st.form_submit_button('Submit B')
                            
                            if submit_click2:
                                
                                st.session_state[f'student_resp2_{i}'] = student_resp2
                                
                                if f'my_form_{i}_submit_click2' not in st.session_state:
                                    st.session_state[f'my_form_{i}_submit_click2'] = True

                                if target_tok.lower() in student_resp2.lower():
                                    st.success(feedback[item]['response_2']['correct'])
                                    st.form_submit_button('Next feedback item')
                                    st.session_state[f'error_form_{i}'] = True
                                    
                                else:
                                    st.warning(feedback[item]['response_2']['incorrect'])
                                    st.form_submit_button('Next feedback item')
                                    st.session_state[f'error_form_{i}'] = True

                else:
                    st.warning(feedback[item]['llm_explanation'])
                    
                    if f'student_resp3_{i}' in st.session_state:
                        student_resp3 = st.session_state[f'student_resp3_{i}']
                        st.text_input(f"Please rewrite the sentence based on this feedback: ", key=f'resp3_{i}', value=student_resp3)

                    else:
                        student_resp3 = st.text_input(f"Please rewrite the sentence based on this feedback: ", key=f'resp3_{i}')
                        st.session_state[f'student_resp3_{i}'] = student_resp3
                 
                    if f'my_form_{i}_submit_click3' in st.session_state:
                        submit_click3 = st.session_state[f'my_form_{i}_submit_click3']
                        
                    else:
                        submit_click3 = st.form_submit_button('Submit C')
                       
                    if submit_click3:
                        if f'my_form_{i}_submit_click3' not in st.session_state:
                            st.session_state[f'my_form_{i}_submit_click3'] = True
                                
                        st.success("Good job")
                        
                        st.form_submit_button('Next feedback item')
                        st.session_state[f'error_form_{i}'] = True


                # Wait for student input before proceeding to the next step
        #if st.button("Next Item", key=f'next_item_{i}'):
        #    step += 1  # Increment step counter
            #st.empty()  # Clear previous messages


if __name__ == "__main__":
    main()