import docx

doc = docx.Document()

doc.settings.element.append(
    docx.oxml.OxmlElement('w:hideSpellingErrors')
)
doc.settings.element.append(
    docx.oxml.OxmlElement('w:hideGrammaticalErrors')
)

doc.save('document-nospellcheck.docx')
