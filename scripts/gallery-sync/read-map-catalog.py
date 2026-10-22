"""Read-only runtime CSV -> gallery catalog; copy explicit flags, never infer photo ownership."""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys

STATES = set('Baden-Württemberg|Bayern|Berlin|Brandenburg|Bremen|Hamburg|Hessen|Mecklenburg-Vorpommern|Niedersachsen|Nordrhein-Westfalen|Rheinland-Pfalz|Saarland|Sachsen|Sachsen-Anhalt|Schleswig-Holstein|Thüringen'.split('|'))

def read_catalog(csv_path, map_path):
    raw = Path(csv_path).read_bytes()
    source = Path(map_path).read_bytes()
    match = re.search(r'\b(?:var|const|let)\s+stateNameMap\s*=\s*\{(.*?)\}', source.decode('utf-8'), re.S)
    if not match:
        raise ValueError('无法读取当前地图 stateNameMap；停止，不猜测州名映射')
    aliases = dict(re.findall(r"['\"]([^'\"]+)['\"]\s*:\s*['\"]([^'\"]+)['\"]", match[1]))
    aliases.update({s: s for s in STATES})
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    required = {'ID', 'StoreName', 'StoreType', 'City', 'PostalCode', 'Address', 'State', 'Latitude', 'Longitude'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError('CSV 缺少目录必需字段')
    stores, invalid, blank, seen = [], [], 0, set()
    for line, row in enumerate(reader, 2):
        if not any(str(v or '').strip() for v in row.values()):
            blank += 1
            continue
        value = lambda key: str(row.get(key) or '').strip()
        identity = value('ID')
        if identity:
            if identity in seen:
                raise ValueError('重复门店 ID，拒绝覆盖目录')
            seen.add(identity)
        state = aliases.get(value('State'))
        try:
            lat, lng = float(value('Latitude')), float(value('Longitude'))
            valid = math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180
        except ValueError:
            valid = False
        if not re.fullmatch(r'[1-9][0-9]*', identity) or not value('StoreName') or not value('StoreType') or state not in STATES or not valid:
            invalid.append(line)
            continue
        flags = {key: value(key) for key in ('Geekbar', 'Dojo')}
        if any(flag not in ('', '0', '1') for flag in flags.values()):
            invalid.append(line)
            continue
        stores.append({'id': identity, 'name': value('StoreName'), 'city': value('City'), 'state': state,
                       'mapId': identity, 'postalCode': value('PostalCode'), 'address': value('Address'),
                       'latitude': lat, 'longitude': lng, 'storeType': value('StoreType'),
                       'category': value('Category'), 'geekbar': int(flags['Geekbar'] == '1'),
                       'dojo': int(flags['Dojo'] == '1')})
    if not stores:
        raise ValueError('没有有效地图门店，拒绝清空目录')
    return {'columns': reader.fieldnames, 'stores': stores, 'sourceSha256': hashlib.sha256(raw).hexdigest(),
            'stateMapSha256': hashlib.sha256(source).hexdigest(), 'valid': len(stores),
            'blank': blank, 'invalidRows': invalid, 'brandFlagsUsed': False,
            'brandFlagsCopiedForMapLinks': True}

if __name__ == '__main__':
    try:
        print(json.dumps(read_catalog(sys.argv[1], sys.argv[2]), ensure_ascii=False))
    except (ValueError, OSError, IndexError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
