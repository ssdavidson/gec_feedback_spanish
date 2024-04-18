from inference_MT5_gec import correct_grammar

from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline
from transformers import pipeline
from langchain.prompts import PromptTemplate
from langchain.schema import StrOutputParser
from operator import itemgetter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import torch

import argparse
import os, re, json, sys
import shutil
import helper_functions

import spacy
import errant
from nltk import sent_tokenize


OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

#Remove before publishing
OPENAI_API_KEY='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'

nlp = spacy.load('es_core_news_md')
annotator = errant.load('es', nlp)


def gec(input_essay):

    # create temp directory
    try:
        os.mkdir('tmp')
    except:
        pass

    orig_lines = []

    for sent in sent_tokenize(input_essay):
        # remove original tokenize spaces
        sent = sent.strip()
        doc = nlp.tokenizer(sent)
        tokens = [token.text for token in doc]
        # whether to put utterances in the same line or not
        orig_lines.append(" ".join(tokens))

    # predict
    num_return_sequences = 1

    cor_lines = []

    for sent in orig_lines:
        sent_results = correct_grammar(sent, num_return_sequences)
        sent_out = sent_results[0].strip()
        doc = nlp.tokenizer(sent_out)
        tokens = [token.text for token in doc]
        cor_lines.append(" ".join(tokens))

    # # generate corrections
    edits = []
    #add sent index to keep track of which sent the edits belong to
    sent_index = 0
    for orig, cor in zip(orig_lines, cor_lines):
        orig_parse = annotator.parse(orig)
        cor_parse = annotator.parse(cor)
        sent_edits = annotator.annotate(orig_parse, cor_parse)
        for edit in sent_edits:
            print(edit.to_m2(id=0))
        if not isinstance(sent_edits, list):
            sent_edits = [sent_edits]
        edits.append((orig_parse, cor_parse, sent_edits, sent_index))
        sent_index += 1

    return edits, cor_lines



def rank_errors(edit_list):
    initial_target_list = ['R:VERB:SVA', 'R:VERB:INFL', 'R:PREP:WC', 'M:PRON', 'U:PRON', 'R:VERB:TENSE', 'R:NOUN:NUM', 'R:VERB:FORM', 'M:PREP', 'M:DET', 'U:PREP', 'M:VERB', 'R:MORPH']

    num_errors = 0
    out_edits = []

    ### Printing errors for testing
    errors_tagged = []
    for sent in edit_list:
        for edit_item in sent[2]:
            errors_tagged.append(edit_item.type)

    print(f"Number of errors tagged {len(errors_tagged)}")
    print(errors_tagged)
    ### End printing errors for testing

    #max errors presented per dialogue == 3 (this is something we need to test)
    types_presented = [] #used to track what error types have already been shown to student
    
    for target in initial_target_list:
        for sent in edit_list:
            for edit_item in sent[2]:
                edit_type = edit_item.type
                if num_errors >= 3:
                    break
                n = 1
                if target in edit_type and types_presented.count(target) < n:
                    #limit number of corrections for specific target to 1 per sentence
                    #limit to N errors of a given type presented to student for entire essay.
                    orig_sent = sent[0]
                    cor_sent = sent[1]
                    sent_index = sent[3]
                    out_edits.append((orig_sent, cor_sent, edit_item, target, sent_index))
                    num_errors += 1
                    types_presented.append(target)
                    break
                    
        if num_errors >= 3:
            break

    return out_edits


def generate_feedback(errors_to_present, l1, level):
    out_dict = {}
    error_count = 0
    
    llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY)

    #level = 1
    #l1 = 'english'
    #original = "Yo estoy feliz con mi mismo."

    prompt2 = ChatPromptTemplate.from_messages([
        ("system", "You are the teacher of a Spanish {level} course. You are writing corrections for a student whose native language is {l1}. You want to provide your students with feedback about mistakes in their writing. Given an original sentence written by a student, and a corrected version of the sentence written by you, explain to the student why you made the corrections you made. Don't change either sentence. Just explain the differences between them in terms of grammar in a way a student can understand."),
        ("user", "Original sentence: {original}\nCorrected Sentence: {corrected}")
    ])

    chain2 = (    prompt2
                | llm
                | StrOutputParser()
             )

    
    for error in errors_to_present:
        #unpack edit tuple
        orig_sentence = error[0]
        cor_sentence = error[1]
        edit_item = error[2]
        target = error[3]

        if "R:VERB:SVA" in target:
            #Don't know if I should include the full sentence
            response_short = "In this sentence '{orig_sent}' you made a mistake on the verb '{orig_tok}'. The correct verb form here is '{cor_tok}'. Remember to make your verbs agree with their subjects. Here's the corrected sentence: {cor_sent}".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str, cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "In this sentence '{orig_sent}' you made a mistake on the verb '{orig_tok}'. What verb form should you have used?".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str)
            response_1_correct = "Good job. Remember to make your verbs agree with their subjects."
            response_1_incorrect = "Not quite. Think about subject-verb agreement. How should your verb be changed to agree with the subject '{subject}'?".format(subject=helper_functions.get_subject_phrase(orig_sentence))
            response_2_correct = "Good job. Remember to make your verbs agree with their subjects."
            response_2_incorrect = "Good try, but not quite. It's tricky, I know. The correct verb form here is '{cor_tok}'. Remember to make your verbs agree with their subjects. Here's the corrected sentence: {cor_sent}".format(cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1
            
        elif "R:VERB:INFL" in target:
            #Don't know if I should include the full sentence
            response_short = "In this sentence '{orig_sent}' you made a mistake on the verb '{orig_tok}'. The correct verb form here is '{cor_tok}'. Remember to make your verbs agree with their subjects. Here's the corrected sentence: {cor_sent}".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str, cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "In this sentence '{orig_sent}' you made a mistake on the verb '{orig_tok}'. What verb form should you have used?".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str)
            response_1_correct = "Good job. Remember to make your verbs agree with their subjects."
            response_1_incorrect = "Not quite. Think about subject-verb agreement. How should your verb be changed to agree with the subject '{subject}'?".format(subject=helper_functions.get_subject_phrase(orig_sentence))
            response_2_correct = "Good job. Remember to make your verbs agree with their subjects."
            response_2_incorrect = "Good try, but not quite. It's tricky, I know. The correct verb form here is '{cor_tok}'. Remember to make your verbs agree with their subjects. Here's the corrected sentence: {cor_sent}".format(cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1

        elif "R:PREP:WC" in target:
            #Don't know if I should include the full sentence
            response_short = "In this sentence '{orig_sent}' you made a mistake on the preposition '{orig_tok}', which doesn't sound natural. I'd recommend using '{cor_tok}' in this case. Here's the corrected sentence: {cor_sent}.".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str, cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})
            
            line_1 = "In this sentence '{orig_sent}' you made a mistake on the preposition '{orig_tok}', which doesn't sound natural. What other preposition should you have used?".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str)
            response_1_correct = "Great! '{cor_tok}' definitely sounds better in this sentence.".format(cor_tok=edit_item.c_str)
            response_1_incorrect = "That still seems a bit off. Think about common prepositions and what might sound better here. Try one more time."
            response_2_correct = "Good job. That's the preposition I'd recommend. Sounds better, right?"
            response_2_incorrect = "I still don't think that's right. I'd recommend using '{cor_tok}' in this case. Here's the corrected sentence: {cor_sent}.".format(cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1

        elif 'M:PRON' in target:
            #Don't know if I should include the full sentence
            response_short = "You seem to be missing a pronoun in the sentence '{orig_sent}'. You should probably include '{cor_tok}' to make the sentence grammatical. Here's the corrected sentence: {cor_sent}".format(orig_sent=orig_sentence.text, cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "You seem to be missing a pronoun in the sentence '{orig_sent}'. How could you improve this sentence by adding a pronoun?".format(orig_sent=orig_sentence.text)
            response_1_correct = "Yep, that's right. '{cor_tok}' is needed to make the sentence grammatical.".format(cor_tok=edit_item.c_str)
            response_1_incorrect = "Not quite. Remember, prepositions and many verbs need an object like 'it' or 'him'. Try again."
            response_2_correct = "Great! '{cor_tok}' is what the sentence was missing.".format(cor_tok=edit_item.c_str)
            response_2_incorrect = "You're still missing something. You should probably include '{cor_tok}' to make the sentence grammatical. Here's the corrected sentence: {cor_sent}".format(cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1
            
        elif 'U:PRON' in target:
            #Don't know if I should include the full sentence
            response_short = "You seem to be using a subject pronoun in the sentence '{orig_sent}'. Often, such pronouns are omitted in Spanish. Here's the corrected sentence: {cor_sent}".format(orig_sent=orig_sentence.text, cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "You seem to be using a pronoun in the sentence '{orig_sent}'. How could you improve this sentence by removing a pronoun?".format(orig_sent=orig_sentence.text)
            response_1_correct = "Yep, that's right. It's better to omit the subject pronoun in this sentence.".format(cor_tok=edit_item.c_str)
            response_1_incorrect = "Not quite. Remember, Spanish doesn't always use subject pronouns. Try again."
            response_2_correct = "Great! Removing the pronoun makes this sentence sound more natural.".format(cor_tok=edit_item.c_str)
            response_2_incorrect = "You're still missing something. You should probably omit the subject pronoun to make the sentence grammatical. Here's the corrected sentence: {cor_sent}".format(cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1

        elif 'R:VERB:TENSE' in target:
            #Don't know if I should include the full sentence
            response_short = "The verb tense you used in '{orig_sent}' isn't quite right. You should probably use '{cor_tok}' instead of '{orig_tok}' here. Here's the corrected sentence: {cor_sent}.".format(cor_tok=edit_item.c_str, orig_tok=edit_item.o_str, cor_sent=cor_sentence.text, orig_sent=orig_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "The verb tense you used in '{orig_sent}' isn't quite right. What would be a better tense of the verb '{lemma}' to use here?".format(orig_sent=orig_sentence.text, lemma=helper_functions.get_lemma(edit_item))
            response_1_correct = "You got it! '{cor_tok}' makes more sense in this context. Remeber, make your verb tenses consistent.".format(cor_tok=edit_item.c_str)
            response_1_incorrect = "You're still a little off. Remeber, you need to make your verb tenses consistent within and between sentences. Give it another try."
            response_2_correct = "Nice! That's exactly what you need. '{cor_tok}' is the right tense for this sentence.".format(cor_tok=edit_item.c_str)
            response_2_incorrect = "Not quite. You should probably use '{cor_tok}' instead of '{orig_tok}' here. Here's the corrected sentence: {cor_sent}.".format(cor_tok=edit_item.c_str, orig_tok=edit_item.o_str, cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1

        elif 'R:NOUN:NUM' in target:
            #Don't know if I should include the full sentence
            response_short = "In '{orig_sent}' you used a {orig_number} noun where you should have used a {cor_number} noun. In this context, the noun {orig_tok} should be the {cor_number} noun {cor_tok}. Here's the corrected sentence: {cor_sent}.".format(orig_sent=orig_sentence.text, orig_number=helper_functions.get_number(edit_item, 'orig'), cor_number=helper_functions.get_number(edit_item, 'cor'), cor_tok=edit_item.c_str, orig_tok=edit_item.o_str, cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "In '{orig_sent}' you used a {orig_number} noun where you should have used a {cor_number} noun. Can you spot the mistake? What would be the right noun form to use?".format(orig_sent=orig_sentence.text, orig_number=helper_functions.get_number(edit_item, 'orig'), cor_number=helper_functions.get_number(edit_item, 'cor'))
            response_1_correct = "That's right! '{cor_tok}' should be plural in this context.".format(cor_tok=edit_item.c_str)
            response_1_incorrect = "That's not the correction I was looking for. Remeber that when you're talking about things 'in general' (like movies or books) you often want to use a plural. Try one more time."
            response_2_correct = "Great! '{cor_tok}' should be plural in this context.".format(cor_tok=edit_item.c_str)
            response_2_incorrect = "That's not the error I was thinking about. In this context, the noun {orig_tok} should be the {cor_number} noun {cor_tok}. Here's the corrected sentence: {cor_sent}.".format(cor_tok=edit_item.c_str, cor_number=helper_functions.get_number(edit_item, 'cor'), orig_tok=edit_item.o_str, cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1

        elif 'R:VERB:FORM' in target:
            #Don't know if I should include the full sentence
            response_short = "In '{orig_sent}' there's an issue with the form of the verb '{orig_tok}'. In this context, the verb '{orig_lemma}' should be the {cor_form} '{cor_tok}'. Here's the corrected sentence: {cor_sent}.".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str, cor_tok=edit_item.c_str, cor_form=helper_functions.get_verb_form(edit_item, 'cor'), orig_lemma=helper_functions.get_lemma(edit_item), cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "In '{orig_sent}' there's an issue with the form of the verb '{orig_tok}'. What would be a better form of this verb to use?".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str)
            response_1_correct = "Exactly! In this sentence you should have used the {cor_form} form '{cor_tok}' instead of the {orig_form} form '{orig_tok}'.".format(cor_tok=edit_item.c_str, orig_tok=edit_item.o_str, cor_form=helper_functions.get_verb_form(edit_item, 'cor'), orig_form=helper_functions.get_verb_form(edit_item, 'orig'))
            response_1_incorrect = "Good try, but that's still a bit off. You should have used {cor_form} form of the verb '{orig_lemma}'. What would that form be?".format(cor_form=helper_functions.get_verb_form(edit_item, 'cor'), orig_lemma=helper_functions.get_lemma(edit_item))
            response_2_correct = "Good job! That's the correct form I was looking for. Remember in English, we usually use participles after helping verbs like 'have' and 'is'."
            response_2_incorrect = "That's still not quite right. In this context, the verb '{orig_lemma}' should be the {cor_form} '{cor_tok}'. Here's the corrected sentence: {cor_sent}.".format(cor_tok=edit_item.c_str, cor_form=helper_functions.get_verb_form(edit_item, 'cor'), orig_lemma=helper_functions.get_lemma(edit_item), cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1

        elif 'M:PREP' in target:
            #Don't know if I should include the full sentence
            response_short = "You seem to be missing a preposition in the sentence '{orig_sent}.' You should probably add '{cor_tok}' to make the sentence sound more natural. Here's the corrected sentence: {cor_sent}".format(orig_sent=orig_sentence.text, cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "You seem to be missing a preposition in the sentence '{orig_sent}' How could you improve the sentence by adding a prepostion?".format(orig_sent=orig_sentence.text)
            response_1_correct = "Yep, that's right. '{cor_tok}' is needed to make the sentence grammatical.".format(cor_tok=edit_item.c_str)
            response_1_incorrect = "Not quite. Remember, a lot of fixed expressions require prepositions, like 'think about' or 'because of'. Try adding a preposition to the sentence one more time."
            response_2_correct = "Great! '{cor_tok}' is what the sentence is missing.".format(cor_tok=edit_item.c_str)
            response_2_incorrect = "You're still missing something. You should probably add '{cor_tok}' to make the sentence sound more natural. Here's the corrected sentence: {cor_sent}".format(cor_tok=edit_item.c_str, cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1

        elif 'U:PREP' in target:
            #Don't know if I should include the full sentence
            response_short = "You seem to have included an unneeded preposition in the sentence '{orig_sent}'. In this context, you should drop the {orig_tok} before {next_tok}. Here's the corrected sentence: {cor_sent}".format(orig_sent=orig_sentence.text, orig_tok=edit_item.o_str, next_tok=helper_functions.get_next_tok(edit_item, orig_sentence), cor_sent=cor_sentence.text)
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})

            line_1 = "You seem to have included an unneeded preposition in the sentence '{orig_sent}'. How could you fix the sentence by removing a prepostion?".format(orig_sent=orig_sentence.text)
            response_1_correct = "That's right. '{orig_tok}' isn't needed in this context, and it makes the sentence sound awkwark.".format(orig_tok=edit_item.o_str)
            response_1_incorrect = "That's not what I was thinking of. Often, people add extra prepostions like to, of and by. Try rewording your sentence again."
            response_2_correct = "Excellent. Dropping the '{orig_tok}' definitely makes this sentence sound better.".format(orig_tok=edit_item.o_str)
            response_2_incorrect = "That still sounds a little off. In this context, you should drop the {orig_tok} before {next_tok}. Here's the corrected sentence: {cor_sent}".format(orig_tok=edit_item.o_str, next_tok=helper_functions.get_next_tok(edit_item, orig_sentence), cor_sent=cor_sentence.text)

            out_dict['edit_' + str(error_count)] = {"response_short": response_short, "llm_explanation": llm_explanation, "line_1":line_1, "response_1":{'correct':response_1_correct, 'incorrect':response_1_incorrect}, 'response_2':{'correct':response_2_correct, 'incorrect':response_2_incorrect}}
            error_count += 1
            
        else:
            llm_explanation = chain2.invoke({"l1": l1, "level": level, "original": orig_sentence, "corrected": cor_sentence})
            out_dict['edit_' + str(error_count)] = {"response_short": '', "llm_explanation": llm_explanation, "line_1":'', "response_1":{'correct':'', 'incorrect':''}, 'response_2':{'correct':'', 'incorrect':''}}


    json_out = json.dumps(out_dict, indent=4)

    return json_out




