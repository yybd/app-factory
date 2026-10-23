#!/bin/bash
# A two-locale listing. en-US: the keyword field repeats "markdown" from the subtitle and
# names a competitor; spaces after commas. he: a Hebrew keyword field of 65
# characters — 120 bytes.
set -euo pipefail
mkdir -p fastlane/metadata/en-US fastlane/metadata/he
printf 'Inkwell' > fastlane/metadata/en-US/name.txt
printf 'Markdown Writing, Focused' > fastlane/metadata/en-US/subtitle.txt
printf 'markdown, notion,editor,notes,writer,rtl,offline' > fastlane/metadata/en-US/keywords.txt
printf 'PRODUCTIVITY' > fastlane/metadata/primary_category.txt
printf 'Inkwell' > fastlane/metadata/he/name.txt
printf 'כתיבה ממוקדת במרקדאון' > fastlane/metadata/he/subtitle.txt
printf 'עורך,פתקים,טקסט,מסמכים,עריכה,ניווט,אופליין,תיקייה,סופר,מחברת,יומן' > fastlane/metadata/he/keywords.txt
