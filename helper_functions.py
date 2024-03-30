def get_subject_phrase(doc):
    for token in doc:
        if ("subj" in token.dep_):
            subtree = list(token.subtree)
            start = subtree[0].i
            end = subtree[-1].i + 1
            return doc[start:end]

def get_lemma(edit_item):
    tokens = edit_item.o_toks
    out_str = ''
    for token in tokens:
        out_str += token.lemma_
    return out_str

def get_number(edit_item, type):
    if type == "orig":
        token = edit_item.o_toks[0]
    if type == "cor":
        token = edit_item.c_toks[0]
    if 'Number' in token.morph:
        number = token.morph.get('Number')[0]
    else:
         number = ''
    return number

def get_verb_form(edit_item, type):
    if type == "orig":
        token = edit_item.o_toks[0]
    if type == "cor":
        token = edit_item.c_toks[0]
    if "VerbForm" in token.morph:
        verb_form = token.morph.get('VerbForm')
    else:
        verb_form = None
    if "VerbTense" in token.morph:
        verb_tense = token.morph.get('Tense')
    else:
        verb_tense = None
    form_map = {'Inf':'infinitive', 'Fin':'finite', 'Part':'particple'}
    tense_map = {'Pres':'present', 'Past':'past'}
    form_string = ''
    tense_string = ''
    if verb_form:
        form_string = form_map[verb_form[0]]
    if verb_tense:
        tense_string = tense_map[verb_tense[0]]
    out_string = "{} {}".format(tense_string,form_string)
    return out_string

def get_next_tok(edit_item, sentence):
    index = edit_item.o_end
    try:
        next_tok = sentence[index].text
    except:
        next_tok = ''
    return next_tok
