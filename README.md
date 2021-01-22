# banquepostale_to_csv

As La Banque Postale sucks and does not provide an easy way
to export data older than a few month in a usable format (ie. NOT pdf) I have created
this script to convert all the Banque Postale relevé in PDF to a CSV format.

I hope you'll find it useful

# Usage
`pdftotext` needs to be installed.

Under linux you can install it by typing:
```shell
sudo apt-get install poppler-utils
```

To run the pdf to csv converter run:
```shell
python3 banquepostale_to_csv.py pdf_folder
```
where `pdf_folder` is the folder containing all the PDF relevés.

# Alternatives

@oaubert has forked this project and developped the following alternative which might be of interest: https://github.com/oaubert/banquepostale-pdf-to-tsv
