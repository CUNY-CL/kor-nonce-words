The lexicon is from [here](https://github.com/CUNY-CL/wikipron/tree/master/data/scrape).

To use, run:

    curl -O https://raw.githubusercontent.com/CUNY-CL/wikipron/master/data/scrape/tsv/kor_hang_narrow.tsv
    pip install -r requirements.txt
    ./generate.py
    # Annotate for lexicality.
    ./stratify.py
