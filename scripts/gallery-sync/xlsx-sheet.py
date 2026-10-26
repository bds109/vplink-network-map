#!/usr/bin/env python3
"""xlsx-sheet-v1: replay the approved worksheet export, never edit business values.

Preserve explicit rows/cells and blanks; serialize UTF-8 CSV with LF and minimal
quoting. Latitude/Longitude use Decimal quantization to 8 places (half-even),
then trim trailing zeroes. Formulas, errors and unsupported cell types fail closed.
"""
import csv
import io
import posixpath
import re
import sys
from decimal import Decimal, localcontext
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def text(element):
    return ''.join(element.itertext()) if element is not None else ''


def column(reference):
    match = re.fullmatch(r'([A-Z]+)[1-9][0-9]*', reference)
    if not match:
        raise ValueError()
    number = 0
    for char in match[1]:
        number = number * 26 + ord(char) - 64
    if number > 16384:
        raise ValueError()
    return number - 1


def convert(original, worksheet):
    if not worksheet or len(worksheet) > 31 or any(ord(c) < 32 for c in worksheet):
        raise ValueError()
    with ZipFile(io.BytesIO(original)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or sum(x.file_size for x in archive.infolist()) > 64 * 1024 * 1024:
            raise ValueError()
        shared = [text(x) for x in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', NS)] if 'xl/sharedStrings.xml' in names else []
        links = {x.attrib['Id']: x for x in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        sheets = ET.fromstring(archive.read('xl/workbook.xml')).findall('m:sheets/m:sheet', NS)
        selected = [x for x in sheets if x.attrib['name'] == worksheet]
        if len(selected) != 1:
            raise ValueError()
        link = links[selected[0].attrib['{' + NS['r'] + '}id']]
        if link.attrib.get('TargetMode', 'Internal') != 'Internal' or not link.attrib['Type'].endswith('/worksheet'):
            raise ValueError()
        target = link.attrib['Target']
        target = posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/' + target)
        if not target.startswith('xl/'):
            raise ValueError()
        rows = []
        previous = 0
        for row in ET.fromstring(archive.read(target)).findall('m:sheetData/m:row', NS):
            row_number = int(row.attrib['r'])
            if row_number <= previous:
                raise ValueError()
            previous = row_number
            cells = {}
            for cell in row.findall('m:c', NS):
                reference = cell.attrib['r']
                index = column(reference)
                if int(re.search(r'[0-9]+$', reference)[0]) != row_number or index in cells or cell.find('m:f', NS) is not None:
                    raise ValueError()
                kind = cell.attrib.get('t')
                value = cell.find('m:v', NS)
                if kind == 's':
                    i = int(value.text)
                    if i < 0:
                        raise ValueError()
                    result = shared[i]
                elif kind == 'inlineStr':
                    result = text(cell.find('m:is', NS))
                elif kind in (None, 'n', 'str'):
                    result = value.text if value is not None and value.text is not None else ''
                else:
                    raise ValueError()
                cells[index] = result
            if not cells:
                continue
            if not rows:
                width = max(cells) + 1
            if any(value for index, value in cells.items() if index >= width):
                raise ValueError()
            values = [cells.get(i, '') for i in range(width)]
            if rows:
                for field in ('Latitude', 'Longitude'):
                    index = rows[0].index(field)
                    if values[index]:
                        with localcontext() as context:
                            context.prec = 50
                            number = Decimal(values[index])
                            if not number.is_finite():
                                raise ValueError()
                            values[index] = format(number.quantize(Decimal('0.00000001')), 'f').rstrip('0').rstrip('.')
            rows.append(values)
        if not rows or not {'ID', 'Latitude', 'Longitude'}.issubset(rows[0]) or len(set(rows[0])) != len(rows[0]):
            raise ValueError()
        output = io.StringIO(newline='')
        csv.writer(output, lineterminator='\n', quoting=csv.QUOTE_MINIMAL).writerows(rows)
        return output.getvalue().encode('utf-8')


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError()
        sys.stdout.buffer.write(convert(sys.stdin.buffer.read(), sys.argv[1]))
    except Exception:
        # Private names/cells must not leak into Actions or operator error output.
        sys.stderr.write('XLSX worksheet conversion failed\n')
        sys.exit(1)
