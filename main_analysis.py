"""
Программа "QRP‑Stat" предназначен для  анализа файла ADIF для вывода статистики по странам и локаторам в зависимости от используемой мощности. Результаты анализа ориентированы на таблицы активности Клуба 72: http://club-72.ru/#qrp.

Данный скрипт создан на основе кода, написанного Андреем UB3BBB. Далее код доработан совместными усилиями двух искусственных интеллектов — Manus и DeepSeek. Они помогли структурировать логику и сделать анализ максимально полезным.

Скрипт распространяется по принципу «как есть» (AS IS): авторы и ИИ-помощники не несут ответственности за возможные ошибки, потерю данных или неверные расчёты. Никаких претензий, исков или требований не принимается. Однако мы будем очень рады, если вы поделитесь найденными проблемами, конструктивной критикой или идеями по улучшению.

Пишите на почту: andrey.R4NCU@gmail.com. Ваше мнение поможет сделать скрипт лучше для всех.
"""
import sys
import os
import re
from datetime import datetime
from collections import Counter, defaultdict
import adif_io
from pyhamtools import locator, LookupLib, Callinfo
import time

STR = {
    'ru': {
        'header': 'ОБЩАЯ СТАТИСТИКА ПО ВСЕМ ADIF ФАЙЛАМ',
        'date': 'Дата анализа',
        'files_count': 'Количество проанализированных файлов',
        'total_qso': 'Общее количество QSO',
        'your_locator': 'Ваш локатор',
        'all_power': 'все мощности',
        'watts': 'Ватт',
        'mw': 'мВт',
        'all_section': 'ОБЩАЯ СТАТИСТИКА ПО ВСЕМ СВЯЗЯМ',
        'cat_section': 'СТАТИСТИКА ПО {name}-СВЯЗЯМ (до {pwr} включительно)',
        'count': 'Количество {name}-связей',
        'odx_label': 'ODX самая дальняя связь',
        'odx_detail': 'Расстояние: {dist} км, мощность: {pwr}',
        'countries': 'Количество сработанных стран (WKD countries)',
        'fields': 'Количество сработано полей (WKD fields)',
        'squares': 'Количество сработано квадратов (WKD squares)',
        'top20': 'ТОП-20 САМЫХ ЧАСТЫХ ПОЗЫВНЫХ (ОБЩАЯ СТАТИСТИКА)',
        'times': 'раз(а)',
        'bands': 'СТАТИСТИКА ПО ДИАПАЗОНАМ (С ODX)',
        'qsos': 'связей',
        'km': 'км',
        'extra': 'ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ',
        'unique_calls': 'Всего уникальных позывных',
        'avg_qso': 'Среднее количество QSO на позывной',
        'processed_files': 'Обработанные файлы',
    },
    'en': {
        'header': 'OVERALL STATISTICS FOR ALL ADIF FILES',
        'date': 'Analysis date',
        'files_count': 'Number of files analyzed',
        'total_qso': 'Total QSO count',
        'your_locator': 'Your locator',
        'all_power': 'all power levels',
        'watts': 'W',
        'mw': 'mW',
        'all_section': 'OVERALL STATISTICS FOR ALL QSOs',
        'cat_section': 'STATISTICS FOR {name} QSOs (up to {pwr} inclusive)',
        'count': 'Number of {name} QSOs',
        'odx_label': 'ODX longest contact',
        'odx_detail': 'Distance: {dist} km, power: {pwr}',
        'countries': 'Countries worked (WKD countries)',
        'fields': 'Fields worked (WKD fields)',
        'squares': 'Squares worked (WKD squares)',
        'top20': 'TOP-20 MOST FREQUENT CALLSIGNS (OVERALL)',
        'times': 'time(s)',
        'bands': 'BAND STATISTICS (WITH ODX)',
        'qsos': 'QSOs',
        'km': 'km',
        'extra': 'ADDITIONAL INFORMATION',
        'unique_calls': 'Total unique callsigns',
        'avg_qso': 'Average QSOs per callsign',
        'processed_files': 'Processed files',
    }
}


def parse_power_custom(pwr_str):
    if not pwr_str:
        return 99999.0
    pwr_str = str(pwr_str).strip().upper().replace(',', '.')
    text_map = {'QRP': 5.0, 'QRPP': 1.0, 'QRP-X': 0.1, 'QRPX': 0.1, 'QRP-U': 0.01, 'QRPU': 0.01}
    if pwr_str in text_map:
        return text_map[pwr_str]
    if pwr_str == "" or (not re.search(r'^[\d\.\s]+', pwr_str)):
        return 99999.0
    dig_sel = re.search(r'[(\d+\.?\d*)|(\.\d+)]+', pwr_str)
    if dig_sel:
        try:
            return float(dig_sel.group())
        except:
            return 99999.0
    return 99999.0


def get_base_call(call):
    if not call:
        return ""
    parts = call.upper().split('/')
    if len(parts) == 1:
        return parts[0]
    return max(parts, key=len)


def normalize_locator(loc):
    if not loc:
        return ""
    loc = loc.strip().upper()
    loc = re.sub(r'[^A-Z0-9]', '', loc)
    if len(loc) == 4:
        return loc + "MM"
    if len(loc) >= 6:
        return loc[:6]
    return loc


def get_call_info(call, cic, max_retries=3):
    if not call or not cic:
        return None, None

    for attempt in range(max_retries):
        try:
            loc = None
            try:
                pos = cic.get_lat_long(call)
                if pos and 'latitude' in pos and 'longitude' in pos:
                    loc = locator.latlong_to_locator(pos["latitude"], pos["longitude"])
                    loc = normalize_locator(loc)
            except:
                pass

            country = None
            try:
                country = cic.get_country_name(call).upper()
            except:
                pass

            if loc or country:
                return loc, country

            time.sleep(0.5)
        except:
            time.sleep(1)

    return None, None


def locator_to_latlon(loc):
    if not loc or len(loc) < 4:
        return None, None
    loc = loc.upper()
    lon = (ord(loc[0]) - 65) * 20 + (ord(loc[2]) - 48) * 2
    lat = (ord(loc[1]) - 65) * 10 + (ord(loc[3]) - 48)
    if len(loc) >= 6:
        lon += (ord(loc[4]) - 65) * (2.0 / 24) + 1.0 / 24
        lat += (ord(loc[5]) - 65) * (1.0 / 24) + 0.5 / 24
    else:
        lon += 1
        lat += 0.5
    return lat - 90, lon - 180


def calculate_distance_approx(loc1, loc2):
    try:
        def loc_to_coords(loc):
            loc = loc.upper()
            lon = (ord(loc[0]) - 65) * 20 + (ord(loc[2]) - 48) * 2
            if len(loc) >= 5:
                lon += (ord(loc[4]) - 65) * (2/24)
            lat = (ord(loc[1]) - 65) * 10 + (ord(loc[3]) - 48)
            if len(loc) >= 6:
                lat += (ord(loc[5]) - 65) * (1/24)
            return lat - 90, lon - 180

        lat1, lon1 = loc_to_coords(loc1)
        lat2, lon2 = loc_to_coords(loc2)

        R = 6371
        lat1, lon1, lat2, lon2 = map(lambda x: x * 3.14159 / 180, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = (dlat/2)**2 + (dlon/2)**2 * (lat1 + lat2)/2
        c = 2 * (a**0.5) if a <= 1 else 2
        return R * c
    except:
        return 0


def analyze_files(file_list, my_loc_str, output_file, power_override=None, lang='ru', collect_map_data=False):
    s = STR.get(lang, STR['ru'])

    my_loc_str = normalize_locator(my_loc_str)

    map_data = [] if collect_map_data else None
    my_lat, my_lon = locator_to_latlon(my_loc_str) if collect_map_data else (None, None)

    cic = None
    try:
        lib = LookupLib(lookuptype="countryfile")
        cic = Callinfo(lib)
    except Exception:
        pass

    act_list = [
        ["ALL", float('inf'), 0, [0.0, "", 0.0], set(), set(), set()],
        ["QRP", 5.0, 0, [0.0, "", 0.0], set(), set(), set()],
        ["QRPp", 1.0, 0, [0.0, "", 0.0], set(), set(), set()],
        ["QRP-X", 0.1, 0, [0.0, "", 0.0], set(), set(), set()],
        ["QRPu", 0.01, 0, [0.0, "", 0.0], set(), set(), set()]
    ]

    all_calls = []
    bands_count = Counter()
    bands_odx = defaultdict(lambda: [0.0, ""])

    call_cache = {}
    total_qsos = 0

    for adif_file in file_list:
        try:
            with open(adif_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            qsos, header = adif_io.read_from_string(content)
        except Exception:
            continue

        for qso in qsos:
            total_qsos += 1

            full_call = qso.get('call', '').upper()
            if not full_call:
                continue

            base_call = get_base_call(full_call)
            all_calls.append(base_call)

            band = qso.get('band', '').upper()
            if not band:
                freq = qso.get('freq', '')
                if freq:
                    try:
                        freq_mhz = float(freq)
                        if freq_mhz < 2: band = '160M'
                        elif freq_mhz < 4: band = '80M'
                        elif freq_mhz < 8: band = '40M'
                        elif freq_mhz < 15: band = '30M'
                        elif freq_mhz < 22: band = '20M'
                        elif freq_mhz < 25: band = '17M'
                        elif freq_mhz < 28: band = '15M'
                        elif freq_mhz < 30: band = '12M'
                        elif freq_mhz < 55: band = '10M'
                        else: band = '2M'
                    except:
                        band = 'Unknown'
                else:
                    band = 'Unknown'

            bands_count[band] += 1

            if power_override is not None:
                pwr = power_override
            else:
                pwr_val = qso.get('tx_pwr') or qso.get('power') or qso.get('app_rumlog_power')
                pwr = parse_power_custom(pwr_val)

            loc = normalize_locator(qso.get('gridsquare', ''))
            country = qso.get('country', '') or qso.get('dxcc', '')

            if (not loc or not country) and cic:
                if base_call in call_cache:
                    cached_loc, cached_country = call_cache[base_call]
                    if not loc and cached_loc:
                        loc = cached_loc
                    if not country and cached_country:
                        country = cached_country
                else:
                    new_loc, new_country = get_call_info(base_call, cic)
                    call_cache[base_call] = (new_loc, new_country)
                    if not loc and new_loc:
                        loc = new_loc
                    if not country and new_country:
                        country = new_country

            dist = 0.0
            if loc and my_loc_str and len(loc) >= 4 and len(my_loc_str) >= 4:
                try:
                    dist = float(locator.calculate_distance(my_loc_str, loc))
                except:
                    try:
                        dist = calculate_distance_approx(my_loc_str, loc)
                    except:
                        dist = 0.0

            if dist > bands_odx[band][0]:
                bands_odx[band] = [dist, full_call]

            for i in range(len(act_list)):
                if pwr <= act_list[i][1]:
                    act_list[i][2] += 1
                    if country:
                        act_list[i][4].add(str(country).upper())
                    if loc and len(loc) >= 2:
                        act_list[i][5].add(loc[:2])
                    if loc and len(loc) >= 4:
                        act_list[i][6].add(loc[:4])
                    if dist > act_list[i][3][0]:
                        act_list[i][3] = [dist, full_call, pwr]

            if collect_map_data and loc and len(loc) >= 4 and my_lat is not None:
                cats = ['ALL']
                if pwr <= 0.01:
                    cats.append('QRPu')
                if pwr <= 0.1:
                    cats.append('QRP-X')
                if pwr <= 1.0:
                    cats.append('QRPp')
                if pwr <= 5.0:
                    cats.append('QRP')
                lat, lon = locator_to_latlon(loc)
                if lat is not None:
                    map_data.append({
                        'call': full_call,
                        'lat': lat,
                        'lon': lon,
                        'band': band,
                        'power': pwr,
                        'dist': dist,
                        'cats': cats
                    })

    def fmt_pwr(val):
        if val < 0.01:
            return f"{val * 1000:.2f} {s['mw']}"
        elif val < 1:
            return f"{val * 1000:.0f} {s['mw']}"
        else:
            return f"{val:.1f} {s['watts']}"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"{s['header']}\n")
        f.write(f"{s['date']}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{s['files_count']}: {len(file_list)}\n")
        f.write(f"{s['total_qso']}: {total_qsos}\n")
        f.write(f"{s['your_locator']}: {my_loc_str}\n")
        f.write("=" * 80 + "\n\n")

        for item in act_list:
            name, max_pwr, count, odx, countries, fields, squares = item

            if name == "ALL":
                power_display = s['all_power']
            else:
                power_display = fmt_pwr(max_pwr)

            if name == "ALL":
                f.write(f"  {s['all_section']} ({power_display})\n")
            else:
                f.write(f"  {s['cat_section'].format(name=name, pwr=power_display)}\n")
            f.write("-" * 60 + "\n")
            f.write(f"   - {s['count'].format(name=name)}: {count}\n")

            if odx[0] > 0:
                f.write(f"   - {s['odx_label']}: {odx[1]}\n")
                f.write(f"     \\_ {s['odx_detail'].format(dist=f'{odx[0]:.1f}', pwr=fmt_pwr(odx[2]))}\n")
            else:
                f.write(f"   - {s['odx_label']}: -\n")

            f.write(f"   - {s['countries']}: {len(countries)}\n")
            f.write(f"   - {s['fields']}: {len(fields)}\n")
            f.write(f"   - {s['squares']}: {len(squares)}\n\n")

        f.write("=" * 80 + "\n")
        f.write(f"{s['top20']}\n")
        f.write("-" * 60 + "\n")
        top_20 = Counter(all_calls).most_common(20)
        for i, (c, cnt) in enumerate(top_20, 1):
            f.write(f"   {i:2}. {c:15} -> {cnt:3} {s['times']}\n")
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write(f"  {s['bands']}\n")
        f.write("-" * 60 + "\n")

        band_order = ['160M', '80M', '40M', '30M', '20M', '17M', '15M', '12M', '10M', '6M', '2M', '70CM', 'Unknown']
        for b in band_order:
            if b in bands_count:
                cnt = bands_count[b]
                dist_val, call_val = bands_odx[b]
                if dist_val > 0:
                    f.write(f"   - {b:6} -> {cnt:4} {s['qsos']}. ODX: {call_val:12} ({dist_val:.1f} {s['km']})\n")
                else:
                    f.write(f"   - {b:6} -> {cnt:4} {s['qsos']}. ODX: -\n")
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write(f"  {s['extra']}\n")
        f.write("-" * 60 + "\n")
        f.write(f"   - {s['unique_calls']}: {len(set(all_calls))}\n")
        f.write(f"   - {s['avg_qso']}: {total_qsos / len(set(all_calls)):.1f}\n")

        f.write(f"\n   {s['processed_files']}:\n")
        for fname in file_list:
            f.write(f"      - {os.path.basename(fname)}\n")

    if collect_map_data:
        return map_data, my_lat, my_lon


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 60)
        print("ADIF ANALYZER - COMBINED STATISTICS")
        print("=" * 60)
        print("\nUsage:")
        print("  python main_analysis.py <file.adif> [locator]")
        print("  python main_analysis.py <folder> [locator]")
        print("\nExamples:")
        print("  python main_analysis.py log.adi LO48VI")
        print("  python main_analysis.py /path/to/folder/ LO48VI")
        print("\nPower categories:")
        print("  * QRP   - up to 5 W")
        print("  * QRPp  - up to 1 W")
        print("  * QRP-X - up to 0.1 W (100 mW)")
        print("  * QRPu  - up to 0.01 W (10 mW)")
        print("=" * 60)
        sys.exit(1)

    adif_path = sys.argv[1]
    my_loc = sys.argv[2] if len(sys.argv) > 2 else "LO48VI"

    if os.path.isdir(adif_path):
        files = [os.path.join(adif_path, f) for f in os.listdir(adif_path)
                if f.lower().endswith(('.adi', '.adif'))]
        if not files:
            print(f"No ADIF files in {adif_path}")
            sys.exit(1)
        output_file = os.path.join(adif_path, f"combined_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    else:
        files = [adif_path]
        output_file = os.path.splitext(adif_path)[0] + "_stats.txt"

    analyze_files(files, my_loc.upper(), output_file)
