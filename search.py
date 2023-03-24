import streamlit as st
import pandas as pd
import re
from string import punctuation
import gdown
import whoosh
from whoosh import index
from whoosh import qparser

st.title('Port Authority Minutes Simple Search')

if 'page_count' not in st.session_state:
    st.session_state['page_count'] = 1

if 'to_see' not in st.session_state:
    st.session_state['to_see'] = 1

if 'start' not in st.session_state:
    st.session_state['start'] = 0

@st.cache
def get_data():
    minutes_url = 'https://drive.google.com/drive/folders/1g_26aBNRMbpL9CC3wrJfVriFP3cBaaeH?usp=sharing'
    gdown.download_folder(minutes_url, quiet=True, use_cookies=False)

get_data()

def escape_markdown(text):
    MD_SPECIAL_CHAR = '\`*_{}#+'
    for char in MD_SPECIAL_CHAR:
        text = text.replace(char,'')
    return text

def no_punct(word):
    return ''.join([letter for letter in word if letter not in punctuation.replace('-','')])

def inject_highlights(text, searches):
    inject = f"""
    <p>
    {' '.join([f"<span style='background-color:#fdd835'>{word}</span>" if no_punct(word.lower()) in searches else word for word in text.split()])}
    </p>
    """
    return inject

def display_text(result, query):
    text = escape_markdown(result['content'])
    searches = re.split('AND|OR|NOT',query)
    searches = [search.strip().lower() for search in searches]

    text = inject_highlights(text, searches)

    st.markdown(f"<small><b>{result['fname']}</b></small>", unsafe_allow_html=True)
    st.markdown(text, unsafe_allow_html=True)
    st.markdown("<hr style='width: 75%;margin: auto;'>", unsafe_allow_html=True)

def index_search(search_fields, search_query, st, en):
    ix = index.open_dir('minutes_index_dir')
    schema = ix.schema

    og = qparser.OrGroup.factory(0.9)
    mp = qparser.MultifieldParser(search_fields, schema, group=og)

    q = mp.parse(search_query)

    with ix.searcher() as s:
        results = s.search(q, limit=None)
        to_full_file = [(res['fname'],res['content']) for res in results]

        to_page = results[st:en]
        to_spec_file = [(res['fname'],res['content']) for res in to_page]

        for result in to_page:
            display_text(result, search_query)

        return to_full_file, to_spec_file

search = st.text_input('Search for a word or phrase')

with st.sidebar:
    if st.button('See next document'):
        st.session_state.start += 1
        st.session_state.to_see += 1
        st.session_state.page_count += 1
    if st.button('See previous document'):
        st.session_state.start -= 1
        st.session_State.to_see -= 1
        st.session_state.page_count -= 1
        
if search != '':
    to_full_file, to_spec_file = index_search(['content'], search, st.session_state.start, st.session_state.to_see)

    st.write(f'Page: {st.session_state.page_count} of {1+ len(to_full_file)//10}')
    
    st.download_button(
        label = 'Download data from this search as a TXT file',
        data = ''.join([f'\n--{ref}--\n{doc}' for ref, doc in to_full_file]).encode('utf-8'),
        file_name = f'pa_minutes_excerpt_{search}.txt',
        mime = 'text/csv'
    )

    st.download_button(
        label = 'Download data just on page this as a TXT file',
        data = ''.join([f'\n--{ref}--\n{doc}' for ref, doc in to_spec_file]).encode('utf-8'),
        file_name = f'pa_minutes_excerpt_{search}.txt',
        mime = 'text/csv'
    )
