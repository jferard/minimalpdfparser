Minimal CSV Parser - Another Python PDF parser

Copyright (C) 2023 J. Férard <https://github.com/jferard>

License: GPLv3


## References
https://pdfa.org/resource/iso-32000-pdf/
https://github.com/adobe-type-tools/agl-aglfn/blob/master/glyphlist.txt
https://www.cs.cmu.edu/~dst/Adobe/Gallery/anon21jul01-pdf-encryption.txt

## Test
```
python3 -m pytest --cov-report term-missing --cov=minimal_pdf_parser && python3 -m pytest --cov-report term-missing --cov-append --doctest-modules --cov=minimal_pdf_parser
```
