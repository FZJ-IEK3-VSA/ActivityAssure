"""
Script for parsing HETUS activity codes from the HETUS 2008 guidelines PDF.

The PDF to be parsed can be obtained here:
https://ec.europa.eu/eurostat/web/products-manuals-and-guidelines/-/ks-ra-08-014
"""

import json
import re

import PyPDF2

if __name__ == "__main__":
    filepath = r".\data\input\Harmonised European time use surveys.pdf"
    start_page = 158
    stop_page = 161
    header = "Eurostat ■ Harmonised European Time Use Surveys"
    footer = "2008 Guidelines - Annex V"
    chapter_title_pattern = r"8 +Activity coding list"
    section_title_pattern = r"8.1 +Main and secondary activities"

    with open(filepath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        assert (
            len(reader.pages) == 210
        ), "Unexpected page count - probably not the expected file"

        # adapt to 0-based index
        pages = reader.pages[start_page - 1 : stop_page]

        text = ""
        for i, page in enumerate(pages):
            page_text = page.extract_text()

            # check for chapter title
            if i == 0:
                page_text = re.sub(chapter_title_pattern, "", page_text)
                page_text = re.sub(section_title_pattern, "", page_text)

            # useful page content is followed by page header and footer
            # --> remove header and everything after
            foundheader = page_text.find(header)
            assert foundheader != -1, "Unexpected page format"
            useful_text = page_text[:foundheader]
            assert (
                len(page_text[foundheader:]) < len(header) + len(footer) + 10
            ), f"Unexpected page format: cutting {len(page_text[foundheader:])} characters after header"
            text += useful_text

    # clean up text
    cleaned_text = text.replace("\r", " ").replace("\n", " ").replace("  ", " ")

    assert (
        m := re.search("\d+ +\d+", cleaned_text)
    ) is None, f"Found two consecutive numbers: {m}"

    # parse activity codes from text
    codes = {}
    matches = re.findall(r"(\d+)([a-z ]+)", cleaned_text, re.IGNORECASE)
    for code, meaning in matches:
        codes[code] = meaning.strip()
    # remark: codes must be stored as strings to keep leading zeros, which are necessary
    # to distinguish e.g. 1 and 01

    # checks and validation
    for code, meaning in codes.items():
        if len(code) < 3:
            # descriptions of 1 or 2 digit codes are always in capitals
            assert (
                meaning.isupper()
            ), f"Validation for 1 and 2 digit codes failed: {code} - {meaning}"
    one_digit_codes = [code for code, m in codes.items() if len(code) == 1]
    assert (
        len(one_digit_codes) == 10
    ), f"Found {len(one_digit_codes)} one-digit-codes instead of 10"
    two_digit_codes = [code for code, m in codes.items() if len(code) == 2]
    assert (
        len(two_digit_codes) == 33
    ), f"Found {len(two_digit_codes)} two-digit-codes instead of 33"

    # hard-coded fixes
    assert "TRAVEL BY PURPOSE" in codes["9"], "Special case different than expected"
    codes["9"] = codes["9"].replace("TRAVEL BY PURPOSE", "").strip()
    assert "AUXILIARY CODES" in codes["900"], "Special case different than expected"
    codes["900"] = codes["900"].replace("AUXILIARY CODES", "").strip()
    assert codes["910"] == "Travel to", "Special case different than expected"
    codes["910"] = "Travel to/from work"
    assert codes["6"] == "SPORTS AND OUTD OOR ACTIVITIES", "Special case different than expected"
    codes["6"] = "SPORTS AND OUTDOOR ACTIVITIES"

    # store as json file
    result_file_path = "./data/input/hetus_activity_codes_2010.json"
    with open(result_file_path, "w+") as result_file:
        json.dump(codes, result_file, indent=4)

    print(f"Created result file {result_file}")
