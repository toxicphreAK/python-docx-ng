Feature: Read content wrapped in a structured document tag
  In order to extract text and values from a document produced from a Word template
  As a developer using python-docx
  I need content controls to be transparent for reading and reachable for inspection


  Scenario: Text inside a block-level content control appears in document.paragraphs
    Given a document containing content controls
     Then document.paragraphs includes the paragraphs inside the content controls
      And document.tables includes the table inside a content control


  Scenario: Text inside a run-level content control appears in paragraph.runs
    Given a document containing content controls
     Then paragraph.runs includes the runs inside a run-level content control
      And paragraph.text includes the text of a run-level content control


  Scenario: Access the content controls themselves
    Given a document containing content controls
     Then document.content_controls has an item for each control in the document
      And each content control knows its tag, alias and type
      And a content control knows when it is showing its placeholder
      And a content control knows the text it contains
