import docx

document = docx.Document()

paragraph = document.add_paragraph('Some text')  # create new paragraph
paragraph.add_footnote('footnote text')  # add a footnote

document.save('document-fotnote.docx')
