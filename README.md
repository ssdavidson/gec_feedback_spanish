# GEC Feedback Generation

Provides a function that takes in a user's text and generates grammar edits and corresponding feedbacks.

Currently configured for Spanish feedback generation. The following should be changed for alternative languages:

* GEC model used (current model is MT5 fine-tuned on COWS-L2H GEC data)
* Errant and Spacy settings
* Target tagset for prioritizing feedback
* Feedback templates if the current versions do not omit desired target errors.

## Installation

### Requried Packages

<!-- Recommend Python version: 3.7 -->

```bash
pip install -r requirements.txt
python3 -m spacy download es
git clone https://github.com/ssdavidson/errant_sp_3.git
cd errant_sp_3
pip install -e .
python3 -m spacy download es_core_news_md
```

### ML Model

Decompress the `.tar.gz` file ([Download Link](https://drive.google.com/file/d/1-tuD6I0uhvBERDIY5UFIccF2drzk6XJ6/view)) and put folder `eracond_T5_model` in the workspace.
