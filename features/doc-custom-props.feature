Feature: Read and write custom document properties
  In order to attach application metadata to a document
  As a developer using python-docx
  I need read/write access to the custom document properties

  Scenario: Set a custom document property
    Given a blank document
     When I set a custom document property
     Then the document reports the custom property I set
      And the custom property survives saving and reopening
