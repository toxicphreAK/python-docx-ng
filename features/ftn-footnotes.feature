Feature: Add and read document footnotes
  In order to annotate a document with notes at the foot of the page
  As a developer using python-docx
  I need access to the footnotes of a document


  Scenario: Access the footnotes of a document having none
    Given a document having no footnotes part
     Then document.footnotes has zero footnotes


  Scenario: Add a footnote and reference it from a run
    Given a document having no footnotes part
     When I add a footnote and reference it from a run
     Then document.footnotes has one footnote
      And the footnote knows its id and text
      And the run holds a reference to the footnote


  Scenario: Footnotes survive a round-trip
    Given a document having no footnotes part
     When I add a footnote and reference it from a run
      And I save the document
     Then the reloaded document reports the footnote
      And the reloaded document keeps the separator footnotes out of the collection
