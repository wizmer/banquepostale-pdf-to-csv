import os
import re
import subprocess

import pandas as pd

months = {month: i + 1 for i, month in enumerate(['janvier', 'février', 'mars', 'avril', 'mai',
                                                  'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'])}


def txt_to_dataframe(filename):
    with open(filename, 'r') as f:
        txt = ''.join(f.readlines())

    header = 'Date      Opérations                                                                            Débit (¤)         Crédit (¤)'

    match_date = re.search(r'Relevé édité le (\d+) (\w+) (\d\d\d\d)', txt)
    day, month, year = match_date.groups()
    year = int(year)
    published_month = months[month]
    the_date = (year, published_month, int(day))
    m = re.search( r'Compte Courant Postal n° \d\d \d\d\d \d\d[A-Z] \d\d\d.*?(Date +Opérations.*?(Nouveau solde.*?\n))', txt, re.DOTALL)
    ccp = m.groups()[0].split('\n')
    # ancien_solde, operations, nouveau_solde = m.groups()
    solde = float(re.search(' (-?\d+(,\d+)?)$',
                            ccp[-2]).groups()[0].replace(',', '.'))

    pages = re.findall(
        r'(Date +Opérations.*?)(Page|Nouveau solde)', m.groups()[0], re.DOTALL)

    m = re.search(
        r'Total des opérations +((\d ?)+(,\d+)?)(?: +((\d ?)+(,\d+)?))?', ccp[-4])
    debit, _, _, credit, _, _ = m.groups()
    debit = float(debit.replace(' ', '').replace(',', '.'))
    if credit:
        credit = float(credit.replace(' ', '').replace(',', '.'))
    else:
        credit = 0

    def page_to_df(page, year):

        lines = page.split('\n')
        # Something scanned lines may start with spaces, so we strip them.
        lines = list(map(lambda l: l.lstrip(), lines))
        # Find the end of "Débit (€)", so we can consider values as credits
        #  if they are locate before this column.
        # Ex:
        # Date   Opérations   Débit(€)  Crédit($)
        # 01/01  Some text      123,45
        # 02/01  Other text                456,67
        credit_col_end = lines[0].find(")")

        def no_junk(s):
            junks = [r"^Date",
                     r"Débit.*Crédit",
                     r"^$",
                     r"Ancien solde au",
                     r"Page \d+/\d+",
                     r"Relevé n° \d+ \| \d{2}/\d{2}/\d{4}",
                     r"MR COSTE BENOIT$",
                     r"Vos opérations CCP n°.*(suite)"]
            return not re.search('|'.join(junks), s)
        cleaned = filter(no_junk, lines)
        grouped = list()
        for l in cleaned:
            if re.match("(^ ?|\n)\d{2}/\d{2}", l):
                grouped.append(list())
            grouped[-1].append(l)

        date = list()
        title = list()
        details = list()
        amount = list()
        for g in grouped:
            if the_date < (2017, 3, 1):
                # before 1st march 2017, there is an extra column with the price in
                # francs
                re_value = r' *(\d{2})\/(\d{2})(.*?)(\d{,3}(?: \d{3})*(,\d+)?) +((?:-|\+ )\d{,3}(?: \d{3})*(?:,\d+)?)$'
                day, month, text, value, cents, value_francs = re.match(
                    re_value, g[0]).groups()
                value = float(value.replace(' ', '').replace(',', '.'))
                value = -value if value_francs[0] == '-' else value

            else:
                re_value = r' *(\d{2})\/(\d{2})(.*?)(\d{,3}(?: \d{3})*(,\d+)?)$'
                day, month, text, value, cents = re.match(
                    re_value, g[0]).groups()
                value = float(value.replace(' ', '').replace(',', '.'))
                value = -value if len(g[0]) <= credit_col_end else value

            if published_month == 1 and month == '12':
                year -= 1
            timestamp = '{}/{}/{}'.format(year, month, day)
            date.append(timestamp)
            amount.append(value)
            title.append(text.strip().lower())
            details.append('\n'.join(g[1:]).strip())
        df = pd.DataFrame({'date': date, 'title': title,
                           'details': details, 'amount': amount})
        return df

    df = pd.concat([page_to_df(m[0], year)
                    for m in pages]).reset_index(drop=True)
    df_credit = df[df.amount > 0]
    if df_credit.size:
        sum_credit = df_credit.amount.sum()
    else:
        sum_credit = 0
    sum_debit = df[df.amount < 0].amount.sum()

    def control_balance(a, b, name):
        if abs(credit - sum_credit) > 1e-6:
            msg = 'ERROR wrong balance for {}\n'.format(name)
            msg += 'Credit says: {}\n'.format(a)
            msg += 'Sum of all credit says: {}\n\n'.format(b)
            raise Exception(msg)

    control_balance(credit, sum_credit, 'credit')
    control_balance(debit, sum_debit, 'debit')
    return df


def txt_folder_to_csv(folder):
    csv_folder = 'csv'
    if not os.path.exists(csv_folder):
        os.makedirs(csv_folder)

    errors = list()
    for f in os.listdir(folder):
        try:
            input_file = os.path.join(folder, f)
            print('Creating csv file from: {}'.format(input_file))
            output_file = os.path.join(csv_folder, f[:-3] + 'csv')
            txt_to_dataframe(input_file).to_csv(output_file, index=False)
        except Exception as e:
            print('Error while doing: {}'.format(f))
            print(e)
            errors.append(f)

    if errors:
        print('There were errors:')
        print(errors)
    else:
        print('Processed OK :)')


def txts_to_dataframe(txt_folder):
    df = pd.concat([txt_to_dataframe(os.path.join(txt_folder, f)) for f in os.listdir(txt_folder)])
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)
    return df

def pdf_folder_to_txt(pdf_folder):
    outfolder = 'txt'
    if not os.path.exists(outfolder):
        os.makedirs(outfolder)

    for f in os.listdir(pdf_folder):
        txt_filename = os.path.join(outfolder, f[:-3] + 'txt')
        print("Creating text file: {}".format(txt_filename))
        subprocess.run(
            ['pdftotext', '-layout', os.path.join(pdf_folder, f), txt_filename])

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python banquepostale_to_csv.py pdf_folder')
        sys.exit(-1)
    pdf_folder_to_txt(sys.argv[1])
    txt_folder_to_csv('txt')
    # txt_to_dataframe('txt/releve_CCP0735738Y028_20130128.txt').to_csv('test.csv', index=False)
