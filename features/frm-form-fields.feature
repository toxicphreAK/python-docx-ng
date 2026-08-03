Feature: Read and fill legacy form fields
  In order to fill in and harvest values from a Word form
  As a developer using python-docx
  I need access to the legacy form fields of a document


  Scenario: Access the form fields of a document
    Given a document containing legacy form fields
     Then document.form_fields has an item for each field in the document
      And each form field knows its name and kind
      And paragraph.form_fields has the fields of that paragraph


  Scenario: Read the value of a form field
    Given a document containing legacy form fields
     Then a text form field knows the text it holds
      And a check box form field knows whether it is ticked
      And a drop-down form field knows the entry selected and the entries offered


  Scenario: Read the settings of a form field
    Given a document containing legacy form fields
     Then a form field knows its help text, status text and enabled state
      And a text form field knows its default, maximum length and text type


  Scenario: Fill in a form and save it
    Given a document containing legacy form fields
     When I assign a new value to each form field
      And I save the document
     Then the reloaded document reports the new values
