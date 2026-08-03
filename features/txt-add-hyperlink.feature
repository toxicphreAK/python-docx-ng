Feature: Add a hyperlink to a paragraph
  In order to link to a web page or to a place in the document
  As a developer using python-docx
  I need a way to create a hyperlink

  Scenario: Add an external hyperlink
    Given a paragraph
     When I add an external hyperlink to the paragraph
     Then the paragraph contains the hyperlink I added
      And the hyperlink has the address I specified
      And the hyperlink text is styled as a hyperlink

  Scenario: Add an internal hyperlink to a bookmark
    Given a document containing a bookmark
     When I add an internal hyperlink to the bookmark
     Then the hyperlink refers to the bookmark by name
      And the hyperlink survives saving and reopening
