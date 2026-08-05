# Working with Documents

`python-docx` allows you to create new documents as well as make changes to existing ones. Actually, it only lets you make changes to existing documents; it's just that if you start with a document that doesn't have any content, it might feel at first like you're creating one from scratch.

This characteristic is a powerful one. A lot of how a document looks is determined by the parts that are left when you delete all the content. Things like styles and page headers and footers are contained separately from the main content, allowing you to place a good deal of customization in your starting document that then appears in the document you produce.

Let's walk through the steps to create a document one example at a time, starting with two of the main things you can do with a document, open it and save it.

## Opening a document

The simplest way to get started is to open a new document without specifying a file to open:

    from docx import Document

    document = Document()
    document.save('test.docx')

This creates a new document from the built-in default template and saves it unchanged to a file named 'test.docx'. The so-called "default template" is actually just a Word file having no content, stored with the installed `python-docx` package. It's roughly the same as you get by picking the *Word Document* template after selecting Word's **File \> New from Template...** menu item.

## REALLY opening a document

If you want more control over the final document, or if you want to change an existing document, you need to open one with a filename:

    document = Document('existing-document-file.docx')
    document.save('new-file-name.docx')

Things to note:

- You can open any Word 2007 or later file this way (`.doc` files from Word 2003 and earlier won't work). Macro-enabled `.docm` files and `.dotx` / `.dotm` templates open too.
- Not every part of a document has an API yet — embedded OLE objects and charts, for instance. Anything without one is left untouched and written back out unchanged on save, so opening and re-saving a document never silently discards content it does not understand.
- If you use the same filename to open and save the file, `python-docx` will obediently overwrite the original file without a peep. You'll want to make sure that's what you intend.

## Files that cannot be opened

A few kinds of file look like an ordinary `.docx` and are not one. Each raises something
that says which:

| Raised | Meaning |
| --- | --- |
| `PackageNotFoundError` | No file at that path, or the file is not a readable OPC package — a truncated download, or not a zip archive at all. |
| `EncryptedPackageError` | The document is password-protected. It is an OLE compound file wrapping the encrypted package, so it cannot be read without the password. Subclasses `PackageNotFoundError`. |
| `StrictOoxmlNotSupportedError` | The document was saved as **Strict Open XML Document**, an option in Word's Save As dialogue and the default in some regulated environments. It uses the same element names in the ISO Strict namespaces rather than the Transitional ones this library reads. Re-saving from Word as "Word Document (.docx)" converts it. |
| `ValueError` | The package is a valid OPC package but not a Word one — a `.xlsx` or `.pptx`, for instance. |

## Opening a 'file-like' document

`python-docx` can open a document from a so-called *file-like* object. It can also save to a file-like object. This can be handy when you want to get the source or target document over a network connection or from a database and don't want to (or aren't allowed to) interact with the file system. In practice this means you can pass an open file or StringIO/BytesIO stream object to open or save a document like so:

    f = open('foobar.docx', 'rb')
    document = Document(f)
    f.close()

    # or

    with open('foobar.docx', 'rb') as f:
        source_stream = StringIO(f.read())
    document = Document(source_stream)
    source_stream.close()
    ...
    target_stream = StringIO()
    document.save(target_stream)

The `'rb'` file open mode parameter isn't required on all operating systems. It defaults to `'r'` which is enough sometimes, but the 'b' (selecting binary mode) is required on Windows and at least some versions of Linux to allow Zipfile to open the file.

Okay, so you've got a document open and are pretty sure you can save it somewhere later. Next step is to get some content in there ...
